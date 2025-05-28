from config import Config
from __init__ import create_app
# from MecheyePackage.mecheye_trigger import TriggerWithExternalDeviceAndFixedRate

# mecheye_trigger = TriggerWithExternalDeviceAndFixedRate

# connect_to_mecheye = mecheye_trigger.main

app, socketio = create_app()

if __name__ == '__main__':
    socketio.run(app, host=Config.HOST, port=Config.PORT,
                allow_unsafe_werkzeug=True,debug=False)