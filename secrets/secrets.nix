let
  autumnal_macmini = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIM7SXkreRFT8Eb3+1WS+5Fz/5W2LuExLfsa7qFUS9k6Y";
  users = [ autumnal_macmini ];

  lebenshilfe-uslar = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILemhXOyzzMCg8s1vgvbdiC8ZM/6lG03eoweISHtfRWt";
in
{
  "nextcloud-secret.age".publicKeys = [ lebenshilfe-uslar ] ++ users;
  "nextcloud-backup-pj92-env.age".publicKeys = [ lebenshilfe-uslar ] ++ users;
  "nextcloud-backup-pj92-encryption.age".publicKeys = [ lebenshilfe-uslar ] ++ users;
  "lebenshilfe-cms-secret.age".publicKeys = [ lebenshilfe-uslar ] ++ users;
}
