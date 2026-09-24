============================================================
SFM BRING NEAR: PROPS
============================================================

Moves selected props or character models into useful positions around a model
or scene camera.

Bring Near moves model positions only. Rotation, scale, parenting, and existing
position animation are preserved.


------------------------------------------------------------
INSTALLATION
------------------------------------------------------------

1. Extract this ZIP into:

       SourceFilmmaker\game\

2. Restart Source Filmmaker.


------------------------------------------------------------
USAGE
------------------------------------------------------------

1. In the Animation Set Editor, select the models you want to move.

2. Right-click the model or scene camera you want to use as the fixed point.

3. Run:

       Bring Near: Props

4. Choose where and how the models should be arranged.

   Placement:

       In Front
       Behind
       Left
       Right

   Row uses one Direction:

       Front / Back (X)
       Left / Right (Y)
       Up / Down (Z)

   Grid uses two directions:

       Columns
       Rows

   Choose different axes for Columns and Rows to set the plane of the grid.

5. Set:

       From model / From camera
       Between models

6. Optional:

   Use the up/down arrows to change the model order.

7. Click:

       Bring Near

To undo the move, press Ctrl+Z.


------------------------------------------------------------
ADDING OR CHANGING MODELS
------------------------------------------------------------

To add more models, leave Bring Near open. Select the models, right-click one
of them, and run the script again.

The fixed point stays the same.

To change the fixed point, close Bring Near. Then right-click and run the
script again on the model or camera you want to use as the new fixed point.


------------------------------------------------------------
PLACEMENT NOTES
------------------------------------------------------------

Row places models in a single line.

Grid arranges models in columns and rows. The two direction controls determine
which plane the grid occupies.

For example:

       Columns: Left / Right (Y)
       Rows:    Up / Down (Z)

creates an upright grid.

Using Front / Back (X) for one direction can instead create a floor or depth
grid.

Distances are measured from model root transforms.

A scene camera can be the fixed point. Bring Near: Props does not move cameras
or lights.


------------------------------------------------------------
VERSION NOTES
------------------------------------------------------------

1.0.1
- Added separate Columns and Rows controls for choosing the Grid plane.

1.0.0
- Initial release.


------------------------------------------------------------
TROUBLESHOOTING
------------------------------------------------------------

If Bring Near does not appear in the Rig menu:

1. Confirm the ZIP was extracted into:

       SourceFilmmaker\game\

2. Restart Source Filmmaker.

If a model cannot be moved, check whether it is locked, parented, or involved
in another transform relationship.


------------------------------------------------------------
UNINSTALL
------------------------------------------------------------

Delete:

       SourceFilmmaker\game\usermod\scripts\sfm\animset\SFM_Bring_Near_Props.py

Then restart Source Filmmaker.


------------------------------------------------------------
AUTHOR / LICENSE
------------------------------------------------------------

ChadChan3D
ChadChan3D.com/assets/

CC0 1.0 Universal - Public Domain Dedication
https://creativecommons.org/publicdomain/zero/1.0/
