# annoyer
Alarm system to predict when user is distracted &amp; "snap user out of it".

## Usage:
1) When starting for the first time, it will ask to load the sound file to use for the alarm.  (only tested on `.wav` files):

![Load sound](https://github.com/andsmith/annoyer/blob/main/File_dialog.png?raw=true)

(this will be remembered.  To clear this selection, see note below)

2) The main app has three panels:

![Screenshot](https://github.com/andsmith/annoyer/blob/main/Screenshot.png?raw=true)

* Interact with the distraction thermometer:  drag the threshold up and down to set the alarm.  
  Moving the threshold above/below the current probability will sound/silence the alarm.
  * The estimated *time until* the probability of distraction exceeds threshold is at the top.)
  * The estimated *average duration between distractions* is at the bottom.
  
  
* Push the three buttons to stop the alarm and change the alarm duration for next time (or leave it the same.)
You can push before/after the alarm has gone off (this will reset the timer to 0).
  

* See the graph to see if you're getting more/less easily distracted.  User history is loaded & saved each time. 

* To clear settings/history/sound-file selection:  move the file `history.json` to clear the user history / alarm sound file.
## To do:
* make units adaptive on vertical axis of graph
## Credits:
1) Sound clip from here: https://freesound.org/people/deleted_user_2906614/sounds/263621/
