$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$packageRoot = Join-Path $projectRoot 'node_modules\@borndotcom\react-native-godot'
$version = '4.5.1.migeran.2'

if (-not (Test-Path -LiteralPath $packageRoot)) {
	throw 'Instale @borndotcom/react-native-godot antes de preparar a LibGodot.'
}

$downloads = @(
	@{
		Name = 'libgodot-android'
		File = 'libgodot-android.zip'
		Sha256 = '5ad2b0d836e6a207ca695e690ed833326e6aba35f43a788bf17c15eb33475783'
	},
	@{
		Name = 'libgodot-cpp-android'
		File = 'godot-cpp-android.zip'
		Sha256 = 'cdf543419a2397dcdcd25d8266f66cf3200cca3dd1b53c161b1b89e819dab21e'
	}
)

foreach ($download in $downloads) {
	$destination = Join-Path $packageRoot "android\libs\$($download.Name)\$version"
	if (Test-Path -LiteralPath $destination) {
		continue
	}

	$archive = Join-Path ([System.IO.Path]::GetTempPath()) $download.File
	$url = "https://github.com/migeran/libgodot/releases/download/$version/$($download.File)"
	Invoke-WebRequest -Uri $url -OutFile $archive
	$actualHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
	if ($actualHash -ne $download.Sha256) {
		throw "Checksum inválido para $($download.File)."
	}

	New-Item -ItemType Directory -Force -Path $destination | Out-Null
	Expand-Archive -LiteralPath $archive -DestinationPath $destination -Force
	Remove-Item -LiteralPath $archive -Force
}

$workletsCmake = Join-Path $projectRoot 'node_modules\react-native-worklets-core\android\CMakeLists.txt'
$workletsSource = Get-Content -LiteralPath $workletsCmake -Raw
$oldHermesLink = @'
  target_link_libraries(
    ${PACKAGE_NAME}
    hermes-engine::libhermes
  )
'@
$newHermesLink = @'
  if(TARGET hermes-engine::libhermes)
    target_link_libraries(${PACKAGE_NAME} hermes-engine::libhermes)
  else()
    target_link_libraries(${PACKAGE_NAME} hermes-engine::hermesvm)
  endif()
'@
if ($workletsSource.Contains($oldHermesLink)) {
	$workletsSource = $workletsSource.Replace($oldHermesLink, $newHermesLink)
	Set-Content -LiteralPath $workletsCmake -Value $workletsSource -NoNewline
}

$godotHeader = Join-Path $packageRoot 'android\src\main\cpp\native_godot_module_jni.h'
$godotSource = Get-Content -LiteralPath $godotHeader -Raw
$godotSource = $godotSource.Replace("#include <react/jni/CxxModuleWrapper.h>`r`n", '')
$godotSource = $godotSource.Replace("#include <react/jni/CxxModuleWrapper.h>`n", '')
Set-Content -LiteralPath $godotHeader -Value $godotSource -NoNewline

Write-Host 'LibGodot Android e compatibilidade React Native preparadas.'
