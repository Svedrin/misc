# Make an effort to improve privacy a bit for Windows systems through local group policies.

Set-ExecutionPolicy RemoteSigned
Set-PSRepository -Name 'PSGallery' -InstallationPolicy Trusted
Install-Module -Name PolicyFileEditor -RequiredVersion 3.0.0

$MchnDir = "$env:windir\system32\GroupPolicy\Machine\registry.pol"
$UserDir = "$env:windir\system32\GroupPolicy\User\registry.pol"


$machine_policies = @(
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\WindowsUpdate\AU'; name='NoAutoUpdates';  val='0'; type='DWord'}, # Updates enabled
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\WindowsUpdate\AU'; name='AUOptions';      val='3'; type='DWord'}, # Auto download, notify before install
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\DataCollection';   name='AllowTelemetry'; val='0'; type='DWord'}, # Disable Telemetry (Only Enterprise and Server editions)
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\DataCollection';   name='LimitDiagnosticLogCollection';                val='1'; type='DWord'},
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\DataCollection';   name='LimitDumpCollection';                         val='1'; type='DWord'},
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\DataCollection';   name='LimitEnhancedDiagnosticDataWindowsAnalytics'; val='0'; type='DWord'},
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\CloudContent';     name='DisableCloudOptimizedContent';                val='1'; type='DWord'},
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\CloudContent';     name='DisableConsumerAccountStateContent';          val='1'; type='DWord'},
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\SettingSync';      name='DisableCredentialsSettingSync';               val='2'; type='DWord'},
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\SettingSync';      name='DisableCredentialsSettingSyncUserOverride';   val='1'; type='DWord'}
);

$user_policies = @(
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\DataCollection';                name='AllowTelemetry';         val='0'; type='DWord' }, # Disable Telemetry (Only Enterprise and Server editions)
	[pscustomobject]@{key='Software\Microsoft\Windows\CurrentVersion\Policies\DataCollection'; name='MicrosoftEdgeDataOptIn'; val='0'; type='DWord' },
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\CloudContent'; name='DisableTailoredExperiencesWithDiagnosticData'; val='1'; type='DWord' },
	[pscustomobject]@{key='Software\Policies\Microsoft\Windows\CloudContent'; name='DisableThirdPartySuggestions';                 val='1'; type='DWord' }
);

echo "Configuring Machine Policies..."
foreach($policy in $machine_policies){
	Set-PolicyFileEntry -Path $MchnDir -Key $policy.key -ValueName $policy.name -Data $policy.val -Type $policy.type
}

echo "Configuring User Policies..."
foreach($policy in $user_policies){
	Set-PolicyFileEntry -Path $UserDir -Key $policy.key -ValueName $policy.name -Data $policy.val -Type $policy.type
}

gpupdate

echo "Applied Machine Policies:"
Get-PolicyFileEntry -Path $MchnDir -All

echo " "
echo "Applied User Policies:"
Get-PolicyFileEntry -Path $UserDir -All
