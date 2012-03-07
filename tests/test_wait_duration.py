# -*- coding: utf-8 -*-
# kate: replace-tabs off; indent-width 4; indent-mode normal
# vim: ts=4:sw=4:noexpandtab

import sys
sys.path.append('..')
from teer import *

def tick():
	rate = sched.create_rate(10)
	while True:
		print '.',
		sys.stdout.flush()
		yield Sleep(rate)

def world():
	print 'World'
	yield WaitDuration(0.2)
	print 'happy'
	yield WaitDuration(0.2)
	print 'happy'
	yield WaitDuration(0.2)
	print 'happy'
	yield WaitDuration(2)
	print 'but...'

def hello():
	tick_tid = sched.new_task(tick())
	print 'Hello'
	yield WaitDuration(1)
	print 'I am rather shy'
	yield WaitDuration(2)
	print 'I might say it'
	world_tid = sched.new_task(world())
	print 'I\'m not alone'
	yield WaitDuration(0.2)
	print 'I talk'
	yield WaitDuration(0.2)
	print 'I talk'
	yield WaitDuration(0.2)
	print 'Now I stop talking and wait'
	yield WaitTask(world_tid)
	print 'World is dead now'
	yield WaitDuration(1)
	print 'I liked world'
	yield WaitDuration(1)
	print 'Really, I\'m tired, I will die...'
	sched.kill_task(tick_tid)

sched = TimerScheduler()
sched.new_task(hello())
print 'Running scheduler'
sched.run()
print 'All tasks are dead, we better leave this place'

