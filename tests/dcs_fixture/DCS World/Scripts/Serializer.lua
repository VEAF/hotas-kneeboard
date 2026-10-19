-- Test stand-in for DCS's Scripts/Serializer.lua (not redistributable): the same output as its
-- serialize_sorted, which tests/test_lua_tables.py checks against the real one when DCS is there.
module('Serializer', package.seeall)

local Writer = {}
Writer.__index = Writer

function new(fout) return setmetatable({fout = fout}, Writer) end

local function scalar(v)
	if type(v) == 'string' then return string.format('%q', v) end
	return tostring(v)
end

function Writer:serialize_sorted(name, value, level)
	level = level or ''
	self.fout:write(level, name, ' = ')
	if type(value) ~= 'table' then
		self.fout:write(scalar(value), ',\n')
		return
	end
	self.fout:write('{\n')
	local keys = {}
	for k in pairs(value) do table.insert(keys, k) end
	table.sort(keys)
	for _, k in ipairs(keys) do
		local key = type(k) == 'number' and string.format('[%s]', k) or string.format('[%q]', k)
		self:serialize_sorted(key, value[k], level .. '\t')
	end
	self.fout:write(level, level == '' and '}\n' or '},\n')
end
