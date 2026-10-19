local res = external_profile('Config/Input/Aircrafts/common_joystick_binding.lua')
join(res.keyCommands, {
	{combos = {{key = 'JOY_BTN1'}}, down = 3201, cockpit_device_id = 40, value_down = 1.0, name = _('Trim Up'), category = _('Trim')},
})
return res
