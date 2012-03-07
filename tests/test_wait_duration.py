# -*- coding: utf-8 -*-
# kate: replace-tabs off; indent-width 4; indent-mode normal
# vim: ts=4:sw=4:noexpandtab

# Copyright (c) 2012 Stéphane Magnenat, ETHZ Zürich and other contributors
# See file authors.txt for details.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
#   * Neither the name of Stéphane Magnenat, ETHZ Zürich, nor the names
#     of the contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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

