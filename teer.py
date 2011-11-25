# strongly inspired from http://www.dabeaz.com/coroutines/

from collections import deque
import time
import heapq

# ------------------------------------------------------------
#                       === Tasks ===
# ------------------------------------------------------------
class Task(object):
	taskid = 0
	def __init__(self,target):
		Task.taskid += 1
		self.tid     = Task.taskid   # Task ID
		self.target  = target        # Target coroutine
		self.sendval = None          # Value to send

	# Run a task until it hits the next yield statement
	def run(self):
		return self.target.send(self.sendval)

# ------------------------------------------------------------
#                      === Scheduler ===
# ------------------------------------------------------------
class Scheduler(object):
	def __init__(self):
		self.ready   = deque()   
		self.taskmap = {}
		# Tasks waiting for other tasks to exit
		self.exit_waiting = {}
		# Task waiting on conditions
		self.cond_waiting = []
	
	def new(self,target):
		newtask = Task(target)
		self.taskmap[newtask.tid] = newtask
		self.schedule(newtask)
		self.log_task_created(newtask)
		return newtask.tid

	def exit(self,task):
		self.log_task_terminated(task)
		del self.taskmap[task.tid]
		# Notify other tasks waiting for exit
		for task in self.exit_waiting.pop(task.tid,[]):
			self.schedule(task)

	def wait_for_exit(self,task,waittid):
		if waittid in self.taskmap:
			self.exit_waiting.setdefault(waittid,[]).append(task)
			return True
		else:
			return False

	def schedule(self,task):
		self.ready.append(task)
	
	def pause_task(self,task):
		if task:
			try:
				self.ready.remove(task)
			except ValueError:
				return False
			else:
				return True
		else:
			return False
	
	def resume_task(self,task):
		if task and task not in self.ready:
			# execute the resumed task directly once we exit the syscall
			self.ready.appendleft(task)
			return True
		else:
			return False
		
	def wait_duration(self,task,duration):
		self.set_timer_callback(self.current_time()+duration, lambda: self.resume_task(task))
	
	def wait_condition(self,task,condition):
		self.cond_waiting.append((condition, task))
	
	""" test all conditions """
	def test_conditions(self):
		# check which conditions are true
		still_blocked = []
		for condition, task in self.cond_waiting:
			if condition():
				self.schedule(task)
			else:
				still_blocked.append((condition, task))
		self.cond_waiting = still_blocked

	# Run all tasks until none is ready
	def step(self):
		while self.ready:
			task = self.ready.popleft()
			try:
				result = task.run()
				if isinstance(result,SystemCall):
					result.task  = task
					result.sched = self
					result.handle()
					continue
			except StopIteration:
				self.exit(task)
				continue
			self.schedule(task)
	
	# Methods that might or must be overridden by children
	
	# Get current time
	def current_time(self):
		return time.clock()
	
	# Execute function f at time t
	def set_timer_callback(self, t, f):
		raise NotImplementedError('timer callback mechanism must be provided by derived class')
	
	# Log for task created
	def log_task_created(self, task):
		print time.ctime() + " - Task %s (tid %d) created" % (task.target.__name__, task.tid)
	
	# Log for task terminated
	def log_task_terminated(self, task):
		print time.ctime() + " - Task %s (tid %d) terminated" % (task.target.__name__, task.tid)

""" A scheduler that sleeps when there is nothing to do. """
class BlockingScheduler(Scheduler):
	def __init__(self):
		super(BlockingScheduler, self).__init__()
		self.timer_cb = []
		self.timer_counter = 0
	
	def set_timer_callback(self,t, f):
		heapq.heappush(self.timer_cb, [t, self.timer_counter, f])
		self.timer_counter += 1
	
	def run(self):
		while self.timer_cb or self.ready:
			self.step()
			t, counter, f = heapq.heappop(self.timer_cb)
			duration = t - self.current_time()
			if duration < 0:
				raise RuntimeError('Negative sleep duration, task deadline ' + str(t) + ' is in the past by ' + str(-duration) + 'seconds.')
			time.sleep(duration)
			f()
			self.step()
	
# ------------------------------------------------------------
#                   === System Calls ===
# ------------------------------------------------------------

""" Parent of all system calls """
class SystemCall(object):
	""" Called in the scheduler context """
	def handle(self):
		pass

""" Return a task's ID number """
class GetTid(SystemCall):
	def handle(self):
		self.task.sendval = self.task.tid
		self.sched.schedule(self.task)

""" Create a new task, return the task identifier """
class NewTask(SystemCall):
	def __init__(self,target):
		self.target = target
	def handle(self):
		tid = self.sched.new(self.target)
		self.task.sendval = tid
		self.sched.schedule(self.task)

""" Kill a task, return whether the task was killed """
class KillTask(SystemCall):
	def __init__(self,tid):
		self.tid = tid
	def handle(self):
		task = self.sched.taskmap.get(self.tid,None)
		if task:
			task.target.close() 
			self.task.sendval = True
		else:
			self.task.sendval = False
		self.sched.schedule(self.task)

""" Kill multiple tasks, return the list of killed tasks """
class KillTasks(SystemCall):
	def __init__(self,tids):
		self.tids = tids
	def handle(self):
		self.task.sendval = []
		for tid in tids:
			task = self.sched.taskmap.get(tid,None)
			if task:
				task.target.close() 
				self.task.sendval.append(tid)
		self.sched.schedule(self.task)

""" Kill all tasks except a subsett, return the list of killed tasks """
class KillAllTasksExcept(SystemCall):
	def __init__(self,except_tids):
		self.except_tids = except_tids
	def handle(self):
		self.task.sendval = []
		for task in self.sched.taskmap:
			if task.tid not in self.except_tids:
				task.target.close()
				self.task.sendval.append(task)
		self.sched.schedule(self.task)

""" Wait for a task to exit """
class WaitTask(SystemCall):
	def __init__(self,tid):
		self.tid = tid
	def handle(self):
		result = self.sched.wait_for_exit(self.task,self.tid)
		self.task.sendval = result
		# If waiting for a non-existent task,
		# return immediately without waiting
		if not result:
			self.sched.schedule(self.task)

""" Pause a task """
class PauseTask(SystemCall):
	def __init__(self,tid):
		self.tid = tid
	def handle(self):
		task = self.sched.taskmap.get(self.tid,None)
		self.task.sendval = self.sched.pause_task(task)
		self.sched.schedule(self.task)

""" Pause multiple tasks """

""" Resume a task """
class ResumeTask(SystemCall):
	def __init__(self,tid):
		self.tid = tid
	def handle(self):
		task = self.sched.taskmap.get(self.tid,None)
		self.task.sendval = self.sched.resume_task(task)
		self.sched.schedule(self.task)

""" Return the current time """
class GetCurrentTime(SystemCall):
	def handle(self):
		self.task.sendval = self.sched.current_time()
		self.sched.schedule(self.task)

""" Pause current task for a certain duration """
class WaitDuration(SystemCall):
	def __init__(self,duration):
		self.duration = duration
	def handle(self):
		self.sched.wait_duration(self.task, self.duration)
		self.task.sendval = None

""" Pause current task until the condition is true """
class WaitCondition(SystemCall):
	def __init__(self,condition):
		self.condition = condition
	def handle(self):
		self.sched.wait_condition(self.task,self.condition)
		self.task.sendval = None

# ------------------------------------------------------------
#          === Helper functions for System Calls ===
# ------------------------------------------------------------

""" Get identifier of current task """
def get_task_id():
	yield GetTid()

""" Create a new task and return task identifier """
def new_task(target):
	yield NewTask(target)

""" Stop the execution of given task, return whether the task was killed """
def kill_task(tid):
	yield KillTask(tid)

""" Stop the execution of given tasks, return the list of killed tasks """
def kill_tasks(tids):
	killed = []
	for tid in tids:
		if kill_task(tid):
			killed.append(tid)
	return killed

""" Stop the execution of all tasks except a subset, return the tid of killed tasks """
def kill_all_tasks_except(except_tids):
	yield KillAllTasksExcept(except_tids)

""" Pause the execution of given task, return whether the task was paused successfully """
def pause_task(tid):
	yield PauseTask(tid)

""" Pause the execution of given tasks, return the list of paused tasks """
def pause_tasks(tids):
	paused = []
	for tid in tids:
		if pause_task(tid):
			paused.append(tid)
	return paused

""" Resume the execution of given task, return whether the task was resumed successfully """
def resume_task(tid):
	yield ResumeTask(tid)

""" Resume the execution of given tasks, return the list of resumed tasks """
def resume_tasks(tids):
	resumed = []
	for tid in tids:
		if resume_task(tid) :
			resumed.append(tid)
	return resumed

""" Return the current time """
def get_current_time():
	yield GetCurrentTime()

""" Pause current task for a certain duration """
def wait_duration(duration):
	yield WaitDuration(duration)

""" Pause current task until the condition is true """
def wait_conditions(condition):
	yield WaitCondition(condition)


# ------------------------------------------------------------
#           === Helper classes for System Calls ===
# ------------------------------------------------------------

""" Helper class to execute a loop at a certain rate """
def Rate():
	def __init__(self,duration):
		self.duration = duration
		self.last_time = get_current_time()
	def sleep(self):
		cur_time = get_current_time()
		delta_time = self.duration - (cur_time - self.last_time)
		if delta_time > 0:
			wait_duration(delta_time)
		self.last_time = get_current_time()

# TODO list
# - if needed, events