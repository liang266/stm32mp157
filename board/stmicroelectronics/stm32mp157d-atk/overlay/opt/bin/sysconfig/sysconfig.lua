#!/usr/bin/env lua

local argparse = require "argparse"
local Syslog = require "posix.syslog"
local Eeprom = require "eeprom"

function Entry(t)
    --[[
    for k, v in pairs(t) do
      print(k, v)
    end
    --]]
    --info = t
    return t
end

function readEeprom(slaveAddr, memAddr, len)
    local fd, ok, msg, config

    if type(slaveAddr) ~= "number" or type(memAddr) ~= "number" or type(len) ~= "number" then
        return nil, "invaild parameter"
    end

    ok, msg = pcall(Eeprom.open, "/dev/i2c-0")
    if not ok then
        return ok, msg
    end

    fd = msg

    ok, msg = pcall(Eeprom.read, fd, slaveAddr, memAddr, len)
    if not ok then
        return ok, msg
    end

    -- if the "msg" all vaild
    config = msg
    -- we should strip the invaild char
    for k, v in ipairs(table.pack(string.byte(msg, 1, -1))) do
        if v > 127 then
            config = string.sub(msg, 1, k - 1)
            break
        end
    end

    ok, msg = pcall(Eeprom.close, fd)
    if not ok then
        return ok, msg
    end

    return ok, config

end

function convertConfig(str)
    -- convert context of read file to lua format
    --[[
    the origin data end with hex "0x0D"
    Entry{
    pcode="P-200400073"
    hw_ver="V3.2"
    pid="HCQ1-1300-D2"
    sn="42921005411"
    mac0="8C89FA00006D"
    mac1="8C89FA00006E"
    mac2="8C89FA00006F"
    mac3="000000000000"
    mac4="000000000000"
    mac5="000000000000"
    }
    --]]

    -- 1th: replace "0x0D" CR to "0x0A" LF
    str = string.gsub(str, '\r', ',\n')
    --[[
    Entry{,
    pcode="P-200400073",
    hw_ver="V3.2",
    pid="HCQ1-1300-D2",
    sn="42921005411",
    mac0="8C89FA00006D",
    mac1="8C89FA00006E",
    mac2="8C89FA00006F",
    mac3="000000000000",
    mac4="000000000000",
    mac5="000000000000",
    }
    --]]

    -- 2th: replace "{,\n" to "{\n"
    str = string.gsub(str, '{,\n', '{\n')
    --[[
    Entry{
    pcode="P-200400073",
    hw_ver="V3.2",
    pid="HCQ1-1300-D2",
    sn="42921005411",
    mac0="8C89FA00006D",
    mac1="8C89FA00006E",
    mac2="8C89FA00006F",
    mac3="000000000000",
    mac4="000000000000",
    mac5="000000000000",
    }
    --]]

    -- 3th: replace ",\n}" to "\n}"
    str = string.gsub(str, ',\n}', '\n}')
    --[[
    Entry{
    pcode="P-200400073",
    hw_ver="V3.2",
    pid="HCQ1-1300-D2",
    sn="42921005411",
    mac0="8C89FA00006D",
    mac1="8C89FA00006E",
    mac2="8C89FA00006F",
    mac3="000000000000",
    mac4="000000000000",
    mac5="000000000000"
    }
    --]]

    return str
end

function isMacVaild(mac)
    if #mac ~= 12 or mac == "000000000000" then
        return nil
    end
    -- convert to byte and return a table
    local t = { string.byte(mac, 1, -1) }
    for _, v in pairs(t) do
        if (v >= 48 and v <= 57) or (v >= 65 and v <= 70) then
            goto continue
        else
            return nil
        end
        :: continue ::
    end

    return true
end

function setEthernetMac(k, v)
    -- replace "mac?" to "eth?"
    local ether = string.gsub(k, "mac", "eth")
    -- mac invaild?
    v = string.gsub(v, "^[ \t\n\r]+", "")
    local mac = string.upper(v)

    if not isMacVaild(mac) then
        if mac ~= "000000000000" then
            Syslog.syslog(3, string.format("%s mac %s invalid\n", ether, mac))
        end
        return nil
    end
    -- replace mac address "112233445566" to "11:22:33:44:55:66"
    mac = string.gsub(v, "..", "%1:", 5)

    -- ifconfig eth0 hw ether 11:22:33:44:55:66
    local cmd = string.format("ifconfig %s hw ether %s", ether, mac)
    local ret, _, msg = os.execute(cmd)
    if not ret then
        Syslog.syslog(3, string.format("%s error %s", cmd, msg))
    else
        Syslog.syslog(6, string.format("%s success", cmd))
    end

    return ret
end

function getSpecifyEthernetPort(port)
    local filename = string.format("/sys/class/net/%s/address", port)
    local fd = io.open(filename)
    if not fd then
        Syslog.syslog(3, string.format("can not popen %s", filename))
        return nil
    end
    local mac = fd:read("a") or ""
    fd:close()

    return mac
end

function getHostname()
    local fd = io.popen("hostname")
    if not fd then
        Syslog.syslog(3, "can not popen hostname")
        return nil
    end
    local hostname = fd:read("a") or ""
    fd:close()

    -- strip \n and $ character
    hostname = string.gsub(hostname, "\n$", "")
    return hostname
end

function setHostname(hostname)
    local cmd = string.format("hostname %s", hostname)
    os.execute(cmd)
end

function setHostnameForAvahi()
    --[[
    the last three bytes of eth1 append hostname:
    eg:
      current hostname is "hcq1"
      mac address is "00:01:02:03:04:05"
      new hostname is "hcq1-030405
    --]]
    eth1Mac = getSpecifyEthernetPort("eth1") or "unkown"
    hostname = getHostname() or "hcq1"

    Syslog.syslog(6, string.format("eth1 mac is %s, current hostname is %s", eth1Mac, hostname))

    appendStr = string.gsub(eth1Mac, ":", "")
    -- new hostname, lua index start 1 not 0
    hostname = hostname .. "-" .. string.sub(appendStr, 7)
    Syslog.syslog(6, string.format("new hostname is %s", hostname))
    setHostname(hostname)
end

function systemConfig(t, args)
    if type(t) ~= "table" then
        return nil, string.format("arg #1 expect table got %s", type(t))
    end

    -- for ethernet port
    for k, v in pairs(t) do
        -- strip "space \t \n \r"
        k = string.gsub(k, "^[ \t\n\r]+", "")
        if string.lower(string.sub(k, 1, 3)) == "mac" then
            setEthernetMac(k, v)
        end
    end

    -- only action when "-s or --set" true
    if args["set"] then
        -- for avahi mdns server
        setHostnameForAvahi()
    end

    return true
end

function argsParse()
    local parser = argparse("Sysconfig", "A tool for system config")
    parser:argument("slave", "I2C device address[hex]"):args(1)
    parser:argument("memory", "Read or Write start address of I2C device[hex]"):args(1)
    parser:argument("count", "Read or Write count[hex]"):args(1)
    parser:flag("-s --set", "Set hostname from ethernet port mac address")
    parser:flag("-v --version", "Show tool version"):action(function()
        print("2.0.0RC2")
        os.exit(0)
    end)

    return parser:parse()
end

function main()
    local ret = -1
    local ok, msg, fn, config
    --[[ LOG_INFO = 6
    LOG_LOCAL4      160
    LOG_INFO        6
    LOG_LOCAL5      168
    LOG_ERR 3
    LOG_UUCP        64
    LOG_NDELAY      8
    LOG_PID 1
    LOG_USER        8
    LOG_CRIT        2
    LOG_LOCAL3      152
    LOG_FTP 88
    LOG_NEWS        56
    LOG_LPR 48
    LOG_EMERG       0
    LOG_LOCAL7      184
    LOG_LOCAL6      176
    LOG_SYSLOG      40
    LOG_CRON        72
    LOG_LOCAL0      128
    LOG_AUTHPRIV    80
    LOG_DEBUG       7
    LOG_WARNING     4
    LOG_DAEMON      24
    LOG_NOTICE      5
    LOG_AUTH        32
    LOG_LOCAL1      136
    LOG_CONS        2
    LOG_ALERT       1
    LOG_KERN        0
    LOG_MAIL        16
    LOG_LOCAL2      144
    --]]
    local args = argsParse()

    Syslog.syslog(6, "Sysconfig start...")

    ok, msg = readEeprom(tonumber(args["slave"], 16), tonumber(args["memory"], 16), tonumber(args["count"], 16))
    if not ok then
        goto err
    end

    -- msg save the eeprom info
    config = convertConfig(msg)

    -- load() compile into global env always, should use return get the value from function
    ok, msg = load("return " .. config)
    if not ok then
        goto err
    end

    fn = ok

    -- run the config lua function
    ok, msg = pcall(fn)
    if not ok then
        goto err
    end

    -- now msg store the fn result, normal is a table
    systemConfig(msg, args)

    ret = 0
    Syslog.syslog(6, "Sysconfig end...")

    :: err ::
    do
        if ret ~= 0 then
            Syslog.syslog(3, msg)
        end
        os.exit(ret)
    end
end

main()