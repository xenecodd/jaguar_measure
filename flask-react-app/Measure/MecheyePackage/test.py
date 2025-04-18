import sys
sys.path.append('/home/eypan/Downloads/fairino-python-sdk/linux/fairino/')
import Robot
robot = Robot.RPC('192.168.58.2')

print(robot.SetDO(7, 0))