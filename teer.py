# -*- coding: utf-8 -*-
# kate: replace-tabs off; indent-width 4; indent-mode normal
# vim: ts=4:sw=4:noexpandtab

# strongly inspired from http://www.dabeaz.com/coroutines/

from collections import deque
import time
import heapq
import copy
import inspect

# ------------------------------------------------------------
#                       === Tasks ===
# ------------------------------------------------------------
class Task(object):
	""" The object representing a task/co-routine in the scheduler """
	WAIT_ANY = 1
	WAIT_ALL = 2
	taskid = 0
	def __init__(self,target):
		""" Initialize """
		Task.taskid += 1
		self.tid     = Task.taskid   # Task ID
		self.target  = target        # Target coroutine
		self.sendval = None          # Value to send
		self.waitmode = Task.WAIT_ANY
	def __repr__(self):
		""" Debug information on a task """
		return 'Task ' + str(self.tid) + ' (' + self.target.__name__ + ') @ ' + str(id(self))
	def run(self):
		""" Run a task until it hits the next yield statement"""
		return self.target.send(self.sendval)

# ------------------------------------------------------------
#                === Conditional Variables ===
# ------------------------------------------------------------
class ConditionVariable(object):
	""" The basic conditional variable """
	def __init__(self, initval=None):
		""" Initialize """
		self.val = initval
		self.myname = None
	def __get__(self, obj, objtype):
		""" Return the value """
		return self.val
	def __set__(self, obj, val):
		""" Set a value, evaluate conditions for tasks waiting on this variable """
		self.val = val
		self._set_name(type(obj))
		obj._test_conditions(self.myname)
	def _set_name(self, cls, top_level=True):
		""" if unknown, retrieve my own name using introspection """
		if self.myname is None:
			members = cls.__dict__
			# first look into members
			for name, value in members.iteritems():
				if value is self:
					self.myname = name
					break
			# look into parents
			for parent_cls in cls.__bases__:
				self._set_name(parent_cls,False)
			# if not found and top-level, assert
			if top_level:
				assert self.myname is not None

# ------------------------------------------------------------
#                      === Scheduler ===
# ------------------------------------------------------------
class Scheduler(object):
	""" The scheduler base object, do not instanciate directly """
	def __init__(self):
		""" Initialize """
		# Map of all task identifiers to tasks
		self.taskmap = {}
		# Deque of ready tasks
		self.ready   = deque()   
		# Tasks waiting for other tasks to exit, map of: tid => list of tasks
		self.exit_waiting = {}
		# Task waiting on conditions, map of: "name of condition variable" => (condition, task)
		self.cond_waiting = {}
		# Task being paused by another task
		self.paused_in_syscall = set()
		self.paused_in_ready = set()
		# Not running a task initially
		self.current_task = None
	
	# Public API, these functions are safe to be called from within a task or from outside
	
	def list_all_tids(self):
		""" Return all task identifiers """
		return self.taskmap.keys()
	
	def get_current_tid(self):
		""" Return the identifier of current task, None if not called from a task """
		if self.current_task is not None:
			return self.current_task.tid
		else:
			return None
	
	def new_task(self, target):
		""" Create a new task from function target, return the task identifier """
		newtask = Task(target)
		self.taskmap[newtask.tid] = newtask
		self._schedule(newtask)
		self._log_task_created(newtask)
		return newtask.tid
	
	def kill_task(self, tid):
		""" Kill a task, return whether the task was killed """
		task = self.taskmap.get(tid,None)
		if task:
			task.target.close() 
			return True
		else:
			return False
	
	def kill_tasks(self, tids):
		""" Kill multiple tasks, return the list of killed tasks """
		return filter(self.kill_task, tids)
	
	def kill_all_tasks_except(self, tids):
		""" Kill all tasks except a subset, return the list of killed tasks """
		to_kill = filter(lambda tid: tid not in tids, self.list_all_tids())
		return self.kill_tasks(to_kill)

	def pause_task(self, tid):
		""" Pause a task, return whether the task was paused """
		task = self.taskmap.get(tid,None)
		if task is None \
			or task is self.current_task\
			or task in self.paused_in_ready\
			or task in self.paused_in_syscall:
			return False
		if task in self.ready:
			self.ready.remove(task)
			self.paused_in_ready.add(task)
		else:
			self.paused_in_syscall.add(task)
		return True
	
	def pause_tasks(self, tids):
		""" Pause multiple tasks, return the lits of paused tasks """
		return filter(self.pause_task, tids)
	
	def pause_all_tasks_except(self, tids):
		""" Pause all tasks except a subset, return the list of paused tasks """
		to_pause = filter(lambda tid: tid not in tids, self.list_all_tids())
		return self.pause_tasks(to_pause)
	
	def resume_task(self, tid):
		""" Resume a task, return whether the task was resumed successfully """
		task = self.taskmap.get(tid,None)
		if task is None or task is self.current_task:
			return False
		if task in self.paused_in_ready:
			self.paused_in_ready.remove(task)
			self.ready.append(task)
			return True
		elif task in self.paused_in_syscall:
			self.paused_in_syscall.remove(task)
			return True
		return False
	
	def resume_tasks(self, tids):
		""" Resume the execution of multiple tasks, return the list of resumed tasks """
		return filter(self.resume, tids)
	
	def resume_all_tasks_except(self, tids):
		""" Resume all tasks except a subset, return the list of resumed tasks """
		to_resume = filter(lambda tid: tid not in tids, self.list_all_tids())
		return self.resume_tasks(to_resume)
	
	def create_rate(self, rate):
		""" Create a rate object, to have a loop at a certain frequency """
		duration = 1./rate
		initial_time = self.current_time()
		return Rate(duration, initial_time)
	
	def printd(self, msg):
		""" Print something including the current task identifier """
		print "[teer tid: " + str(self.get_current_tid()) + "] " + msg
	
	# Public API, these funtions must be called outside a task
	
	def step(self):
		""" Run all tasks until none is ready """
		if self.current_task is not None:
			raise RuntimeError('Scheduler.step() called within a task.')
		while self.ready:
			task = self.ready.popleft()
			try:
				#print 'Running ' + str(task)
				self.current_task = task
				result = task.run()
				self.current_task = None
				if isinstance(result,SystemCall):
					result.task  = task
					result.sched = self
					result.handle()
					#print 'ready queue B: ' + str(self.ready)
					continue
			except StopIteration:
				self.current_task = None
				self._exit(task)
				continue
			self._schedule(task)
	
	# Public API, these functions are safe to be called from within a task or from outside
	# these functions can be overriden by children
	
	def current_time(self):
		""" Return the current time """
		return time.time()
	
	# Protected implementations, these functions can only be called by functions from this object
	# these functions can be overriden by children
	
	def _sleep(self, duration):
		""" Sleep a certain amount of time """
		time.sleep(duration)
	
	def _set_timer_callback(self, t, f):
		""" Execute function f at time t """
		raise NotImplementedError('timer callback mechanism must be provided by derived class')
	
	def _log_task_created(self, task):
		""" Log for task created """
		print time.ctime() + " - Task %s (tid %d) created" % (task.target.__name__, task.tid)
	
	def _log_task_terminated(self, task):
		""" Log for task terminated """
		print time.ctime() + " - Task %s (tid %d) terminated" % (task.target.__name__, task.tid)
	
	# Protected implementations, these functions can only be called by functions from this object

	def _exit(self,exiting_task):
		""" Handle the termination of a task """
		self._log_task_terminated(exiting_task)
		del self.taskmap[exiting_task.tid]
		# Notify other tasks waiting for exit
		to_remove_keys = []
		for task in self.exit_waiting.pop(exiting_task.tid,[]):
			if task.waitmode == Task.WAIT_ANY:
				# remove associations to other tasks waited on
				for waited_tid, waiting_tasks_list in self.exit_waiting.iteritems():
					# remove task form list of waiting tasks if in there
					for waiting_task in waiting_tasks_list:
						if waiting_task.tid == task.tid:
							waiting_tasks_list.remove(waiting_task)
				# return the tid of the exiting_task 
				task.sendval = exiting_task.tid
				self._schedule(task)
			else:
				are_still_waiting = False
				for waited_tid, waiting_tasks_list in self.exit_waiting.iteritems():
					for waiting_task in waiting_tasks_list:
						if waiting_task.tid == task.tid:
							are_still_waiting = True
				if not are_still_waiting:
					# return the tid of the exiting_task 
					task.sendval = exiting_task.tid
					self._schedule(task)
		self.exit_waiting = dict((k,v) for (k,v) in self.exit_waiting.iteritems() if v)

	def _wait_for_exit(self,task,waittid):
		""" Set task waiting of the exit of task waittid """
		if waittid in self.taskmap:
			self.exit_waiting.setdefault(waittid,[]).append(task)
			return True
		else:
			return False

	def _schedule(self,task):
		if task in self.paused_in_syscall:
			self.paused_in_syscall.remove(task)
			self.paused_in_ready.add(task)
		else:
			self.ready.append(task)
	
	def _schedule_now(self,task):
		if task in self.paused_in_syscall:
			self.paused_in_syscall.remove(task)
			self.paused_in_ready.add(task)
		else:
			self.ready.appendleft(task)
		
	def _wait_duration(self,task,duration):
		def resume(task):
			self._schedule_now(task)
		self._set_timer_callback(self.current_time()+duration, lambda: resume(task))
	
	def _wait_duration_rate(self,task,duration,rate):
		def resume(task,rate):
			# get current time
			rate.last_time = self.current_time()
			# if not paused, execute the resumed task directly once we exit the syscall
			self._schedule_now(task)
		self._set_timer_callback(self.current_time()+duration, lambda: resume(task, rate))
	
	def _add_condition(self,entry):
		condition = entry[0]
		vars_in_cond = dict(inspect.getmembers(dict(inspect.getmembers(condition))['func_code']))['co_names']
		for var in vars_in_cond:
			if var not in self.cond_waiting:
				self.cond_waiting[var] = []
			self.cond_waiting[var].append(entry)
	
	def _del_condition(self,candidate):
		(condition, task) = candidate
		vars_in_cond = dict(inspect.getmembers(dict(inspect.getmembers(condition))['func_code']))['co_names']
		for var in vars_in_cond:
			if var in self.cond_waiting:
				self.cond_waiting[var].remove(candidate)
				if not self.cond_waiting[var]:
					del self.cond_waiting[var]
	
	def _wait_condition(self,task,condition):
		# add a new condition and directly evalutate it once
		entry = (condition,task)
		if not condition():
			self._add_condition(entry)
		else:
			self._schedule_now(task)
		
	def _test_conditions(self, name):
		# is there any task waiting on this name?
		if name not in self.cond_waiting:
			return
		# check which conditions are true
		candidates = copy.copy(self.cond_waiting[name])
		for candidate in candidates:
			(condition, task) = candidate
			if task not in self.paused_in_syscall and condition():
				self._schedule(task)
				self._del_condition(candidate)


class TimerScheduler(Scheduler):
	""" A scheduler that sleeps when there is nothing to do. """
	
	def __init__(self):
		""" Initialize """
		super(TimerScheduler, self).__init__()
		self.timer_cb = []
		self.timer_counter = 0
	
	# Public API, these funtions must be called outside a task
	
	def run(self):
		""" Run until there is no task to schedule """
		if self.current_task is not None:
			raise RuntimeError('TimerScheduler.run() called within a task.')
		while self.timer_cb or self.ready or self.cond_waiting:
			self.step()
			t, counter, f = heapq.heappop(self.timer_cb)
			duration = t - self.current_time()
			if duration >= 0:
				self._sleep(duration)
			f()
			self.step()
	
	def timer_step(self):
		""" Schedule all tasks with past deadlines and step """
		if self.current_task is not None:
			raise RuntimeError('TimerScheduler.timer_step() called within a task.')
		while self.timer_cb:
			t, counter, f = heapq.heappop(self.timer_cb)
			duration = t - self.current_time()
			if duration <= 0:
				f()
			else:
				heapq.heappush(self.timer_cb, [t, counter, f])
				break
		self.step()
	
	# Protected implementations, these functions can only be called by functions from this object
	
	def _set_timer_callback(self, t, f):
		""" Implement the timer callback """
		heapq.heappush(self.timer_cb, [t, self.timer_counter, f])
		self.timer_counter += 1
	
# ------------------------------------------------------------
#                   === Helper objects ===
# ------------------------------------------------------------

class Rate(object):
	""" Helper class to execute a loop at a certain rate """
	def __init__(self,duration,initial_time):
		""" Initialize """
		self.duration = duration
		self.last_time = initial_time
	def sleep(self,sched,task):
		""" Sleep for the rest of this period """
		cur_time = sched.current_time()
		delta_time = self.duration - (cur_time - self.last_time)
		if delta_time > 0:
			sched._wait_duration_rate(task, delta_time, self)
		else:
			sched._schedule(task)
		return delta_time

# ------------------------------------------------------------
#                   === System Calls ===
# ------------------------------------------------------------

class SystemCall(object):
	""" Parent of all system calls """
	def handle(self):
		""" Called in the scheduler context """
		raise NotImplementedError('system call superclass should not be used directly')

class Pass(SystemCall):
	""" Pass the execution to other tasks """
	def handle(self):
		self.task.sendval = True
		self.sched._schedule(self.task)
	
class GetScheduler(SystemCall):
	""" Return the scheduler, useful to access condition variables """
	def handle(self):
		self.task.sendval = self.sched
		self.sched._schedule(self.task)

class WaitTask(SystemCall):
	""" Wait for a task to exit, return whether the wait was a success """
	def __init__(self,tid):
		self.tid = tid
	def handle(self):
		result = self.sched._wait_for_exit(self.task,self.tid)
		self.task.sendval = result
		self.task.waitmode = Task.WAIT_ANY
		# If waiting for a non-existent task,
		# return immediately without waiting
		if not result:
			self.sched._schedule(self.task)

class WaitAnyTasks(SystemCall):
	""" Wait for any tasks to exit, return whether the wait was a success """
	def __init__(self,tids):
		self.tids = tids
	def handle(self):
		self.task.waitmode = Task.WAIT_ANY
		# Check if all tasks exist
		all_exist = True
		non_existing_tid = None
		for tid in self.tids:
			if tid not in self.sched.taskmap:
				all_exist = False
				non_existing_tid = tid
				break
		# If all exist
		if all_exist:
			for tid in self.tids:
				self.sched._wait_for_exit(self.task,tid)
			#dont set sendval, we want exit() to assign the exiting tasks tid
			#self.task.sendval = True
		else:
			# If waiting for a non-existent task,
			# return immediately without waiting
			self.task.sendval = non_existing_tid
			self.sched._schedule(self.task)

class WaitAllTasks(SystemCall):
	""" Wait for all tasks to exit, return whether the wait was a success """
	def __init__(self,tids):
		self.tids = tids
	def handle(self):
		self.task.waitmode = Task.WAIT_ALL
		any_exist = False
		for tid in self.tids:
			result = self.sched._wait_for_exit(self.task,tid)
			any_exist = any_exist or result
		# If waiting for non-existent tasks,
		# return immediately without waiting
		if any_exist:
			self.task.sendval = True			
		else:
			self.task.sendval = False
			self.sched._schedule(self.task)

class WaitDuration(SystemCall):
	""" Pause current task for a certain duration """
	def __init__(self,duration):
		self.duration = duration
	def handle(self):
		self.sched._wait_duration(self.task, self.duration)
		self.task.sendval = None

class WaitCondition(SystemCall):
	""" Pause current task until the condition is true """
	def __init__(self,condition):
		self.condition = condition
	def handle(self):
		self.sched._wait_condition(self.task,self.condition)
		self.task.sendval = None

class Sleep(SystemCall):
	""" Sleep using a rate object """
	def __init__(self,rate):
		self.rate = rate
	def handle(self):
		self.task.sendval = self.rate.sleep(self.sched, self.task)