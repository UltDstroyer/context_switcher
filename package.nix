{ 
  lib,
  stdenvNoCC,
  makeWrapper,
  bash,
  coreutils,
  gnugrep,
  gnused,
  jq,
  procps,
  socat,
  wmctrl,
  util-linux,
  systemd,
  python3,
}:

stdenvNoCC.mkDerivation {
  pname = "context-switcher";
  version = "0.1.0";

  src = ./.;

  nativeBuildInputs = [ makeWrapper ];

  dontBuild = true;

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/bin"

    install -m 0755 src/ctx "$out/bin/ctx"
    install -m 0755 src/ctxd "$out/bin/ctxd"
    install -m 0755 src/ctxdctl "$out/bin/ctxdctl"
    install -m 0755 native-host/firefox_host.py "$out/bin/ctx-firefox-host"
    install -m 0755 native-host/register.sh "$out/bin/ctx-firefox-register"

    runtimePath="$out/bin:${lib.makeBinPath [
      bash
      coreutils
      gnugrep
      gnused
      jq
      procps
      socat
      wmctrl
      util-linux
      systemd
      python3
    ]}"

    wrapProgram "$out/bin/ctx" --prefix PATH : "$runtimePath"
    wrapProgram "$out/bin/ctxd" --prefix PATH : "$runtimePath"
    wrapProgram "$out/bin/ctxdctl" --prefix PATH : "$runtimePath"
    wrapProgram "$out/bin/ctx-firefox-host" --prefix PATH : "$runtimePath"
    wrapProgram "$out/bin/ctx-firefox-register" --prefix PATH : "$runtimePath"

    runHook postInstall
  '';

  meta = {
    description = "Capture, leave, and restore named Linux work contexts";
    homepage = "https://github.com/UltDstroyer/context_switcher";
    platforms = lib.platforms.linux;
    mainProgram = "ctx";
  };
}
