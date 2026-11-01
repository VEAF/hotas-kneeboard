-- a debug message left in a community mod, on stdout in the game's log
print("CommunityPlane joystick", 1)
io.write("CommunityPlane io.write\n")
return {
	keyCommands = {
		{combos = {{key = 'JOY_BTN1'}}, down = 3101, cockpit_device_id = 30, value_down = 1.0, name = _('Tailhook'), category = _('Systems')},
		-- a keyboard key in a joystick profile, as some ED modules have
		{combos = {{key = 'G'}}, down = 3102, cockpit_device_id = 30, value_down = 1.0, name = _('Gear'), category = _('Systems')},
	},
}
