## Do common imports
import time
import os
from rich import print
from expframework.experiment import Experiment
from hive.assembly import ScopeAssembly


## Describe the script. This is important and will be logged in the Experiment system.
__description__ = \
"""
Routine to control microscope for challenge 2 of the EMBO Hack Your Microscope Workshop.
Team: The Schrödinger's Flow
"""


### It is recommended that you include a quick explainer.
print("Use create_exp() to create an experiment.")
print("Use start() to start imging.")

global exp
global scope
scope = ScopeAssembly.current
exp = Experiment.current

def create_exp():
	"""Create an experiment for acquisition"""
	global exp
	exp = Experiment.Construct(["live_dead_ratio", "sch_flow"])

	### Create measurement streams.


## Stage controls ----------------------------------------------
def move_stage(x, y, z):
	"""Relative movement in number of steps"""
	pass
	#scope.stage.move_rel[]

def move_x(x):
	"""After finding focus, only move in x to acquire multiple FOVs."""
	pass

## Stage controls ----------------------------------------------




## Pump controls ----------------------------------------------

def wash_sample(time_sec=2, delay_us=1000):
	scope = ScopeAssembly.current
	scope.ch1.move(steps=int((time_sec*1000)/delay_us),
				   forward= True, 
				   delay_us=delay_us)

def stain_sample(time_sec=2, delay_us=1000):
	scope = ScopeAssembly.current
	scope.ch2.move(steps=int((time_sec*1000)/delay_us),
				   forward= True, 
				   delay_us=delay_us)


def wash_stain_wash(wash_time=2, stain_time=2, delay=2):
	global exp
	wash_sample()
	exp.delay("First wash delay - remove cells that did not adhere", 2)
	stain_sample()
	exp.delay("Staining delay", 2)
	wash_sample()
	exp.delay("Wash the stain delay", 2)
## Pump controls ----------------------------------------------


def acquire_2_channels():
	"""Acquire the two channels from two cameras one by one."""
	pass


