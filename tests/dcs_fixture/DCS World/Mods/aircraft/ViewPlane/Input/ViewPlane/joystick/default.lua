local res = external_profile('Config/Input/Aircrafts/common_joystick_binding.lua')
join(res.keyCommands, {
	{combos = {{key = 'JOY_BTN1'}}, down = 3201, cockpit_device_id = 40, value_down = 1.0, name = _('Trim Up'), category = _('Trim')},
	-- declared a second time, as some modules do (Mi-24P): one command for DCS, same hash
	{combos = {{key = 'JOY_BTN_POV1_U'}}, pressed = 34, up = 214, name = _('View Up slow'), category = _('View')},
})
return res
