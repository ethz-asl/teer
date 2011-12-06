# -*- coding: utf-8 -*-
# kate: replace-tabs off; indent-width 4; indent-mode normal
# vim: ts=4:sw=4:noexpandtab

from teer import *
import threading
import rospy

# ------------------------------------------------------------
#		=== Scheduler working with ROS' time and threading ===
# ------------------------------------------------------------
class ROSScheduler(Scheduler):
	""" A scheduler supporting multi-threading access and ROS time """
	def __init__(self):
		super(ROSScheduler, self).__init__()
		self.wake_cond = threading.Condition()
		self.running = True
		def stop_run():
			self.wake_cond.acquire()
			self.running = False
			self.wake_cond.notify()
			self.wake_cond.release()
		rospy.on_shutdown(stop_run)
	
	def current_time(self):
		return rospy.Time.now().to_sec()
	
	def sleep(self, duration):
		rospy.sleep(duration)
	
	def set_timer_callback(self, t, f):
		def timer_callback(event):
			self.wake_cond.acquire()
			f()
			self.wake_cond.notify()
			self.wake_cond.release()
		rospy.Timer(rospy.Duration(t - self.current_time()), timer_callback, True)
	
	def run(self):
		self.wake_cond.acquire()
		self.step()
		while not rospy.is_shutdown() and self.running:
			self.wake_cond.wait()
			self.test_conditions() # suboptimal, when a timer waked us up, conditions have not changed
			self.step()

# ------------------------------------------------------------
#	 === Conditional Variables working with ROS' threading ===
# ------------------------------------------------------------
class ROSConditionVariable(ConditionVariable):
	""" A conditional variable working with ROSScheduler """
	def __init__(self, initval=None):
		super(ROSConditionVariable, self).__init__(initval)
	def __get__(self, obj, objtype):
		return self.val
	def __set__(self, obj, val):
		obj.wake_cond.acquire()
		self.val = val
		self._set_name(obj)
		obj.wake_cond.notify()
		obj.wake_cond.release()
