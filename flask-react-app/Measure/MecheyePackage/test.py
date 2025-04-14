import sys
sys.path.append('/home/eypan/Downloads/fair_api_old/')
import Robot

robot = Robot.RPC('192.168.58.2')

print(robot.GetActualTCPPose())