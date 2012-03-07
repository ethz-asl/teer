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

def main_task():
	def printer(nr):
		counter = 0
		while counter < nr:
			sched.printd(str(counter) + ' (on ' + str(nr) + ')')
			yield WaitDuration(0.5)
			counter += 1
		sched.printd(str(sched.exit_waiting))

	def test_wait_any():
		id1 = sched.new_task(printer(5))
		id2 = sched.new_task(printer(10))
		ret = yield WaitAnyTasks([id1,id2])
		sched.kill_tasks([id1,id2])
		print ret
	
	def test_wait_all():
		id1 = sched.new_task(printer(5))
		id2 = sched.new_task(printer(10))
		ret = yield WaitAllTasks([id1,id2])
		sched.kill_tasks([id1,id2])
		print ret
	
	print '\n* Test wait any *\n'
	wait_id = sched.new_task(test_wait_any())
	yield WaitTask(wait_id)
	print '\n * Test wait all *\n'
	wait_id = sched.new_task(test_wait_all())
	yield WaitTask(wait_id)

sched = TimerScheduler()
sched.new_task(main_task())
print 'Running scheduler'
sched.run()
print 'All tasks are dead, we better leave this place'

