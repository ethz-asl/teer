#import teer
from teer import *

def go_to(dest, dest_threshold = 1):
	print 'Going to ' + str(dest)
	yield WaitCondition(lambda: dist(pos, dest) > dest_threshold)

def exit_boat_house():
	pass

def start_logging():
	pass

def deploy_probe():
	pass

def local_sample():
	pass

def follow_path(path):
	pass

def depth_control(depth):
	while True:
		print 'Control depth ' + str(depth)
		yield WaitDuration(1)

def energy_check(battery_threshold):
	yield WaitCondition(lambda: battery_level < battery_threshold)
	yield KillAllTasksExcept([get_task_id()])
	rospy.signal_shutdown("Energy too low")

def dense_sample(outer_tasks):
	while True:
		yield WaitCondition(lambda: chlorophyl > 5)
		yield PauseTasks(outer_tasks)
		last_pos = pos
		last_cable_length = cable_length
		local_sample()
		go_to(last_pos)
		set_cable_length(last_cable_length)
		yield WaitCondition([cable_length_done, lambda: pos == last_pos])
		yield ResumeTasks(outer_tasks)

def complex_mission():
	exit_boat_house()
	go_to(starting_point)
	start_logging()
	deploy_probe()

	this_tid = yield GetTaskId()
	depth_control_tid = yield NewTask(depth_control(8))
	these_tasks = [this_tid, depth_control_tid]
	dense_sample_tid = yield NewTask(dense_sample(these_tasks))

	follow_path(x1)

	yield KillTasks([dense_sample_tid, depth_control_tid])

	zigzag_path(x2)

