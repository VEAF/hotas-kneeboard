-- A module whose joystick defaults include the generic hat views, as every ED module's do
declare_plugin("ViewPlane by Test", {
	InputProfiles = {
		["ViewPlane"] = current_mod_path .. '/Input/ViewPlane',
	},
})

make_flyable('ViewPlane', current_mod_path .. '/Cockpit/Scripts/', nil, current_mod_path .. '/comm.lua')
plugin_done()
