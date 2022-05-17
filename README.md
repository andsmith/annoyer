# annoyer
Alarm system to predict when user is distracted &amp; "snap user out of it".

## Usage:
1) run with this command:`> python annoyer.py`

The main app has three panels:

![Screenshot](https://github.com/andsmith/annoyer/blob/main/Screenshot.png?raw=true)

* Interact with the distraction thermometer:  drag the threshold up and down to set the alarm.  
  Moving the threshold above/below the current probability will sound/silence the alarm.  The quantities in the lower left are:
  * Average distraction-free period duration:  Estimate of shape parameter (i.e. 1/rate).
  * Sub-threshold duration:  expected wait time until probability exceeds threshold
  * P(distraction|t):  current probability you are distracted given time passed.
  * Exceeds threshold in:  countdown timer.
  
  
* Push the three buttons to stop the alarm and change the alarm duration for next time (or push the yellow button to leave it the same.)
You can push before or after the alarm has gone off.  Both will reset the timer (in addition to the "Reset timer." button).
  

* Check the graph to see if you're getting more/less easily distracted.  User history is loaded & saved each time. 

* To clear settings/history:  move/delete the file `history.json`.
## To do:
* Add units to x-axis of graph (timestamps/dates?)
## Credits:
1) Sound clip from here: https://freesound.org/people/deleted_user_2906614/sounds/263621/
