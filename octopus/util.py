from time import time as now
from numpy import arange


def timerange (start, interval, step):
	if start < 0:
			start = now() + start

	return arange(start, start + interval, step, float)


