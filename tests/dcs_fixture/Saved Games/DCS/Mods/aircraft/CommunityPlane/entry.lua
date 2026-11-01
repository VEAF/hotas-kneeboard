-- A community module, installed in Saved Games/DCS/Mods/aircraft
-- some community mods print while loading: it must not corrupt the loader's output
print("CommunityPlane entry loaded")
declare_plugin("CommunityPlane by Test", {
	InputProfiles = {
		["CommunityPlane"] = current_mod_path .. '/Input/CommunityPlane',
	},
})
plugin_done()
