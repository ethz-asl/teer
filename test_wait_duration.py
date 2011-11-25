import teer

def world():
	print 'World'
	yield teer.WaitDuration(0.2)
	print 'happy'
	yield teer.WaitDuration(0.2)
	print 'happy'
	yield teer.WaitDuration(0.2)
	print 'happy'
	yield teer.WaitDuration(2)
	print 'but...'

def hello():
	print 'Hello'
	yield teer.WaitDuration(1)
	print 'I am rather shy'
	yield teer.WaitDuration(2)
	print 'I might say it'
	world_tid = yield teer.NewTask(world())
	print 'I\'m not alone'
	yield teer.WaitDuration(0.2)
	print 'I talk'
	yield teer.WaitDuration(0.2)
	print 'I talk'
	yield teer.WaitDuration(0.2)
	print 'Now I stop talking and wait'
	yield teer.WaitTask(world_tid)
	print 'World is dead now'
	yield teer.WaitDuration(1)
	print 'I liked world'
	yield teer.WaitDuration(1)
	print 'Really, I\'m tired, I will die...'

sched = teer.BlockingScheduler()
sched.new(hello())
print 'Running scheduler'
sched.run()
print 'All tasks are dead, we better leave this place'

