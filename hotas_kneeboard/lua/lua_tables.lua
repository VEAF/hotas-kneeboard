-- lua_tables.lua: reads and writes DCS's input files (Config/Input/disabled.lua, *.diff.lua…) the
-- way the game does, for lua_tables.py.
--
-- Input, on stdin (UTF-8), written by lua_tables.py:
--   scripts <DCS install>/Scripts       where DCS's Serializer.lua is
--   read <path>                          prints the value the file returns, as JSON
--   write <path> <name> <length>         followed by <length> bytes of Lua source of a value:
--                                        writes it as DCS does, "local <name> = {…}return <name>"
-- Paths come through stdin: luae.exe reads its command line in the ANSI code page.

local function readLine() return io.read('*l') end

local function fail(msg)
	io.stderr:write(tostring(msg), '\n')
	os.exit(1)
end

-- A table is a JSON array when its keys are exactly 1..n, an object when they are all strings;
-- anything else (a sparse or mixed table) would not survive the trip and is refused.
local function jsonEncode(v)
	local t = type(v)
	if t == 'nil' then return 'null'
	elseif t == 'boolean' then return tostring(v)
	elseif t == 'number' then
		if v ~= v or v == math.huge or v == -math.huge then fail('number not representable: ' .. tostring(v)) end
		return string.format('%.17g', v)
	elseif t == 'string' then
		return '"' .. v:gsub('[%c"\\]', function(c)
			local map = {['"'] = '\\"', ['\\'] = '\\\\', ['\n'] = '\\n', ['\r'] = '\\r', ['\t'] = '\\t'}
			return map[c] or string.format('\\u%04x', c:byte())
		end) .. '"'
	elseif t ~= 'table' then
		fail('value not representable: ' .. t)
	end
	local count, strings = 0, 0
	for k in pairs(v) do
		count = count + 1
		if type(k) == 'string' then strings = strings + 1 end
	end
	if count == 0 then return '{}' end
	if strings == 0 and #v == count then
		local out = {}
		for _, x in ipairs(v) do table.insert(out, jsonEncode(x)) end
		return '[' .. table.concat(out, ',') .. ']'
	end
	if strings ~= count then fail('table with keys of mixed kinds') end
	local keys, out = {}, {}
	for k in pairs(v) do table.insert(keys, k) end
	table.sort(keys)
	for _, k in ipairs(keys) do table.insert(out, jsonEncode(k) .. ':' .. jsonEncode(v[k])) end
	return '{' .. table.concat(out, ',') .. '}'
end

local function loadValue(src, chunkName)
	src = src:gsub('^\239\187\191', '') -- UTF-8 BOM, which Lua 5.1 refuses to load
	local f, err = loadstring(src, chunkName)
	if not f then fail(err) end
	setfenv(f, {})
	local ok, res = pcall(f)
	if not ok then fail(res) end
	return res
end

local scripts = (readLine() or ''):match('^scripts\t(.*)$') or fail('no "scripts" record')
package.path = scripts:gsub('/*$', '', 1) .. '/?.lua;' .. package.path

local line = readLine() or fail('no command')
local readPath = line:match('^read\t(.*)$')
if readPath then
	local file = io.open(readPath, 'rb') or fail('not found: ' .. readPath)
	local src = file:read('*a')
	file:close()
	io.write(jsonEncode(loadValue(src, '@' .. readPath)), '\n')
	return
end

local writePath, name, length = line:match('^write\t(.*)\t([%a_][%w_]*)\t(%d+)$')
if not writePath then fail('unknown command: ' .. line) end
local value = loadValue('return ' .. io.read(tonumber(length)), '=value')
local Serializer = require('Serializer')
-- binary, as the game: its files end their lines with LF only
local file = io.open(writePath, 'wb') or fail('cannot write: ' .. writePath)
Serializer.new(file):serialize_sorted('local ' .. name, value)
file:write('return ' .. name)
file:close()
