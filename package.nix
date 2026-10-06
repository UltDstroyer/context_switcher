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

    runtimePath="$out/bin:${lib.makeBinPath [
      bash
      coreutils
      gnugrep
      gnused
      jq
      procps
      socat
      wmctrl
    ]}"

    wrapProgram "$out/bin/ctx" --prefix PATH : "$runtimePath"
    wrapProgram "$out/bin/ctxd" --prefix PATH : "$runtimePath"
    wrapProgram "$out/bin/ctxdctl" --prefix PATH : "$runtimePath"

    runHook postInstall
  '';

  meta = {
    description = "Capture, leave, and restore named Linux work contexts";
    homepage = "https://github.com/UltDstroyer/context_switcher";
    platforms = lib.platforms.linux;
    mainProgram = "ctx";
  };
}
