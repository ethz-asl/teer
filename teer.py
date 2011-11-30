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

	def __repr__(self):
		return 'Task ' + str(self.tid) + ' (' + self.target.__name__ + ')'
	# Run a task until it hits the next yield statement
	def run(self):
		return self.target.send(self.sendval)

# ------------------------------------------------------------
#                === Conditional Variables ===
# ------------------------------------------------------------
class ConditionalVariable(object):
	def __init__(self, initval=None):
		self.val = initval
	def __get__(self, obj, objtype):
		return self.val
	def __set__(self, obj, val):
		self.val = val
		obj.test_conditions()

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
		#print 'ready queue A: ' + str(self.ready)
		while self.ready:
			task = self.ready.popleft()
			try:
				#print 'Running ' + str(task)
				result = task.run()
				if isinstance(result,SystemCall):
					result.task  = task
					result.sched = self
					result.handle()
					#print 'ready queue B: ' + str(self.ready)
					continue
			except StopIteration:
				self.exit(task)
				continue
			self.schedule(task)
	
	# Methods that might or must be overridden by children
	
	# Get current time
	def current_time(self):
		return time.time()
	
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
class TimerScheduler(Scheduler):
	def __init__(self):
		super(TimerScheduler, self).__init__()
		self.timer_cb = []
		self.timer_counter = 0
	
	# Implement the timer callback
	def set_timer_callback(self,t, f):
		#print 'Set timer callback at ' + str(t) + ' ' + str(self.current_time())
		heapq.heappush(self.timer_cb, [t, self.timer_counter, f])
		self.timer_counter += 1
	
	# Run until there is no task to schedule
	def run(self):
		while self.timer_cb or self.ready:
			self.step()
			t, counter, f = heapq.heappop(self.timer_cb)
			duration = t - self.current_time()
			if duration >= 0:
				time.sleep(duration)
			f()
			self.step()
	
	# Schedule all tasks with past deadlines and step
	def timer_step(self):
		while self.timer_cb:
			t, counter, f = heapq.heappop(self.timer_cb)
			duration = t - self.current_time()
			if duration <= 0:
				f()
			else:
				heapq.heappush(self.timer_cb, [t, counter, f])
				break
		self.step()
	

""" Helper class to execute a loop at a certain rate """
class Rate(object):
	def __init__(self,duration,initial_time):
		self.duration = duration
		self.last_time = initial_time
	def sleep(self,sched,task):
		cur_time = sched.current_time()
		delta_time = self.duration - (cur_time - self.last_time)
		self.last_time = cur_time
		if delta_time > 0:
			sched.wait_duration(task, delta_time)
		else:
			sched.schedule(task)
		return delta_time

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
		for tid in self.tids:
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
		for tid, task in self.sched.taskmap.items():
			if tid not in self.except_tids:
				task.target.close()
				self.task.sendval.append(task)
		self.sched.schedule(self.task)

""" Wait for a task to exit, return whether the wait was a success """
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

""" Pause a taskk, return whether the task was paused successfully """
class PauseTask(SystemCall):
	def __init__(self,tid):
		self.tid = tid
	def handle(self):
		task = self.sched.taskmap.get(self.tid,None)
		self.task.sendval = self.sched.pause_task(task)
		self.sched.schedule(self.task)

""" Pause multiple tasks, return the list of paused tasks """
class PauseTasks(SystemCall):
	def __init__(self,tids):
		self.tids = tids
	def handle(self):
		self.task.sendval = []
		for tid in self.tids:
			task = self.sched.taskmap.get(tid,None)
			if self.sched.pause_task(task):
				self.task.sendval.append(tid)
		self.sched.schedule(self.task)

""" Resume a task, return whether the task was resumed successfully """
class ResumeTask(SystemCall):
	def __init__(self,tid):
		self.tid = tid
	def handle(self):
		task = self.sched.taskmap.get(self.tid,None)
		self.task.sendval = self.sched.resume_task(task)
		self.sched.schedule(self.task)

""" Resume the execution of given tasks, return the list of resumed tasks """
class ResumeTasks(SystemCall):
	def __init__(self,tids):
		self.tids = tids
	def handle(self):
		self.task.sendval = []
		for tid in self.tids:
			task = self.sched.taskmap.get(tid,None)
			if self.sched.resume_task(task):
				self.task.sendval.append(tid)
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

""" Create a rate object, to have loops of certain frequencies """
class CreateRate(SystemCall):
	def __init__(self,rate):
		self.duration = 1./rate
	def handle(self):
		initial_time = self.sched.current_time()
		self.task.sendval = Rate(self.duration, initial_time)
		self.sched.schedule(self.task)

""" Sleep using a rate object """
class Sleep(SystemCall):
	def __init__(self,rate):
		self.rate = rate
	def handle(self):
		self.task.sendval = self.rate.sleep(self.sched, self.task)

# TODO list
# - if needed, events