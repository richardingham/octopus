
from octopus.sequence.runtime import *

v = variable(0, "variable", "variable")

run(

sequence(								#23
	once(v > 4, log("v > 4")),						#2 #1
	wait("2s"),										#3
	loop_while(v < 2, 									#7
		sequence(										#6
			increment(v),								#4
			wait("1 s"),								#5
		)
	),
	parallel(								#15
		loop_until(v > 5, 							#11
			sequence(								#10
				increment(v),							#8
				wait("2 sec"),							#9
			)
		),
		sequence(								#14
			wait_until(v == 4),							#12
			log("V is now 5"),							#13
		),
	),
	do_if(v > 10, log("v > 10"), log("v < 10")),		#18 #16 #17
	do_if(v > 1, log("v > 1"), log("v < 1")),			#21 #19 #20
	log("Done!"),								#22
)

)
