import sys,threading, requests
sys.path.append('/home/eypan/Downloads/')
import Robot, subprocess
from time import sleep
from MecheyePackage.robot_control import send_command
from Scripts import *

robot = Robot.RPC('192.168.58.2')
ok, ret = robot.GetActualJointPosDegree()
# scrc = [-5.9326171875, -74.58998878403466, 91.40015857054455, -196.742946511448, 5.83406656095297, 89.98324856899752]
# ret = robot.MoveJ(scrc, 0, 0, vel=100)
# while(1):
#     if ret[1]<=45:
#         break
#     sleep(0.2)
print("Obtain the current tool pose", ret)



