
local key_win_member    = KEYS[1] .. ARGV[1]
local key_lose_member   = KEYS[1] .. ARGV[2]
local win_members       = redis.call('smembers', key_win_member)
local lose_members      = redis.call('smembers', key_lose_member)

return cmsgpack.pack({ win = win_members, lose = lose_members })
