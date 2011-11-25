import teer

def go_to(dest, dest_threshold = 1):
	print 'Going to ' + str(dest)
	teer.wait_condition(lambda: dist(pos, dest) > dest_threshold)

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
		teer.wait_duration(1)

def energy_check(battery_threshold):
	teer.wait_condition(lambda: battery_level < battery_threshold)
	teer.kill_all_tasks_except([teer.get_task_id()])
	rospy.signal_shutdown("Energy too low")

def dense_sample(outer_tasks):
	while True:
		teer.wait_condition(lambda: chlorophyl > 5)
		teer.pause_tasks(outer_tasks)
		last_pos = pos
		last_cable_length = cable_length
		local_sample()
		go_to(last_pos)
		set_cable_length(last_cable_length)
		teer.wait_condition([cable_length_done, lambda: pos == last_pos])
		teer.resume_tasks(outer_tasks)

def complex_mission():
	exit_boat_house()
	go_to(starting_point)
	start_logging()
	deploy_probe()

	this_tid = teer.get_task_id()
	depth_control_tid = teer.new_task(depth_control(8))
	these_tasks = [this_tid, depth_control_tid]
	dense_sample_tid = teer.new_task(dense_sample(these_tasks))

	follow_path(x1)

	teer.kill_tasks([dense_sample_tid, depth_control_tid])

	zigzag_path(x2)

