-- The part of every module's joystick defaults that puts the slow views on the first hat of every
-- device. The real file uses iCommandView*Slow and iCommandViewStop; their numbers give the same hashes.
return {
	keyCommands = {
		{combos = {{key = 'JOY_BTN_POV1_L'}}, pressed = 32, up = 214, name = _('View Left slow'), category = _('View')},
		{combos = {{key = 'JOY_BTN_POV1_R'}}, pressed = 33, up = 214, name = _('View Right slow'), category = _('View')},
		{combos = {{key = 'JOY_BTN_POV1_U'}}, pressed = 34, up = 214, name = _('View Up slow'), category = _('View')},
		{combos = {{key = 'JOY_BTN_POV1_D'}}, pressed = 35, up = 214, name = _('View Down slow'), category = _('View')},
		{combos = {{key = 'JOY_BTN_POV1_UR'}}, pressed = 210, up = 214, name = _('View Up Right slow'), category = _('View')},
		{combos = {{key = 'JOY_BTN_POV1_DR'}}, pressed = 211, up = 214, name = _('View Down Right slow'), category = _('View')},
		{combos = {{key = 'JOY_BTN_POV1_DL'}}, pressed = 212, up = 214, name = _('View Down Left slow'), category = _('View')},
		{combos = {{key = 'JOY_BTN_POV1_UL'}}, pressed = 213, up = 214, name = _('View Up Left slow'), category = _('View')},
	},
	axisCommands = {},
}
