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
import math

class MyScheduler(TimerScheduler):
	chlorophyll_level = ConditionVariable(0.)
	energy_level = ConditionVariable(100)

def chlorophyll_detector():
	yield WaitCondition(lambda: sched.chlorophyll_level > 2)
	print 'We found chlorophyll'
	yield WaitDuration(2)
	print 'Ok, I\'m green enough'

def energy_monitoring():
	yield WaitCondition(lambda: sched.energy_level < 10)
	print 'No more energy, killing all tasks'
	my_tid = sched.get_current_tid()
	sched.kill_all_tasks_except([my_tid])
	print 'Going for lunch'
	yield WaitDuration(1)
	print 'Mission done'
	
def main_task():
	chlorophyll_tid = sched.new_task(chlorophyll_detector())
	energy_tid = sched.new_task(energy_monitoring())
	while True:
		print 'Performing main business'
		yield WaitDuration(1)

sched = MyScheduler()
sched.new_task(main_task())
print 'Running scheduler'
while sched.taskmap:
	# simulate external conditions
	sched.energy_level -= 3
	sched.chlorophyll_level = math.sin(float(sched.energy_level) / 30.) * 4
	# run ready timers
	sched.timer_step()
	# wait
	time.sleep(0.3)
	print 'Ext var: energy_level=' +str(sched.energy_level)+', chlorophyll_level='+str(sched.chlorophyll_level)
print 'All tasks are dead, we better leave this place'

