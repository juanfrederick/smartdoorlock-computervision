from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
    PushServerError,
    PushTicketError,
)
import os
import requests
from requests.exceptions import ConnectionError, HTTPError
import firebase_admin
from firebase_admin import credentials, db

# cred = credentials.Certificate("dbkey.json")
# firebase_admin.initialize_app(cred, {'databaseURL': 'https://smart-door-lock-58-default-rtdb.asia-southeast1.firebasedatabase.app'})

def loop_send_message(base_title, base_message):
    ref = db.reference()
    user_data = ref.child('lock').child('-NirdTJoPlvLn407NKev').get()
    connected_user = []
    if 'connectedUser' in user_data:
        connected_user = user_data['connectedUser']
    else:
        connected_user = None

    # Optionally providing an access token within a session if you have enabled push security
    session = requests.Session()
    session.headers.update(
        {
            # "Authorization": f"Bearer {os.getenv('EXPO_TOKEN')}",
            "accept": "application/json",
            "accept-encoding": "gzip, deflate",
            "content-type": "application/json",
        }
    )

    # Basic arguments. You should extend this function with the push features you
    # want to use, or simply pass in a `PushMessage` object.
    def send_push_message(token, title, message, extra=None):
        try:
            response = PushClient(session=session).publish(
                PushMessage(to=token,
                            title=title,
                            body=message,
                            data=extra))
        except PushServerError as exc:
            # Encountered some likely formatting/validation error.
            rollbar.report_exc_info(
                extra_data={
                    'token': token,
                    'title': title,
                    'message': message,
                    'extra': extra,
                    'errors': exc.errors,
                    'response_data': exc.response_data,
                })
            raise
        except (ConnectionError, HTTPError) as exc:
            # Encountered some Connection or HTTP error - retry a few times in
            # case it is transient.
            rollbar.report_exc_info(
                extra_data={'token': token, 'title': title, 'message': message, 'extra': extra})
            raise self.retry(exc=exc)

        try:
            # We got a response back, but we don't know whether it's an error yet.
            # This call raises errors so we can handle them with normal exception
            # flows.
            response.validate_response()
        except DeviceNotRegisteredError:
            # Mark the push token as inactive
            from notifications.models import PushToken
            PushToken.objects.filter(token=token).update(active=False)
        except PushTicketError as exc:
            # Encountered some other per-notification error.
            rollbar.report_exc_info(
                extra_data={
                    'token': token,
                    'title': title,
                    'message': message,
                    'extra': extra,
                    'push_response': exc.push_response._asdict(),
                })
            raise self.retry(exc=exc)

    for element in connected_user:
        if element is not None and 'phoneToken' in element:
            phoneToken = element['phoneToken']
            print("Send Message To: " + phoneToken)
            send_push_message(phoneToken, base_title, base_message)
            print(phoneToken + " - Message Sent")
        else:
            print("Skipping element:", element)