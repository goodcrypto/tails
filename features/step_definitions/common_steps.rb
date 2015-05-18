require 'fileutils'

def post_vm_start_hook
  # Sometimes the first click is lost (presumably it's used to give
  # focus to virt-viewer or similar) so we do that now rather than
  # having an important click lost. The point we click should be
  # somewhere where no clickable elements generally reside.
  @screen.click_point(@screen.w, @screen.h/2)
end

def activate_filesystem_shares
  # XXX-9p: First of all, filesystem shares cannot be mounted while we
  # do a snapshot save+restore, so unmounting+remounting them seems
  # like a good idea. However, the 9p modules get into a broken state
  # during the save+restore, so we also would like to unload+reload
  # them, but loading of 9pnet_virtio fails after a restore with
  # "probe of virtio2 failed with error -2" (in dmesg) which makes the
  # shares unavailable. Hence we leave this code commented for now.
  #for mod in ["9pnet_virtio", "9p"] do
  #  $vm.execute("modprobe #{mod}")
  #end

  $vm.list_shares.each do |share|
    $vm.execute("mkdir -p #{share}")
    $vm.execute("mount -t 9p -o trans=virtio #{share} #{share}")
  end
end

def deactivate_filesystem_shares
  $vm.list_shares.each do |share|
    $vm.execute("umount #{share}")
  end

  # XXX-9p: See XXX-9p above
  #for mod in ["9p", "9pnet_virtio"] do
  #  $vm.execute("modprobe -r #{mod}")
  #end
end

def post_snapshot_restore_hook
  $vm.wait_until_remote_shell_is_up
  post_vm_start_hook

  # XXX-9p: See XXX-9p above
  #activate_filesystem_shares

  # The guest's Tor's circuits' states are likely to get out of sync
  # with the other relays, so we ensure that we have fresh circuits.
  # Time jumps and incorrect clocks also confuses Tor in many ways.
  if $vm.has_network?
    if $vm.execute("service tor status").success?
      $vm.execute("service tor stop")
      $vm.execute("rm -f /var/log/tor/log")
      $vm.execute("killall vidalia")
      $vm.host_to_guest_time_sync
      $vm.execute("service tor start")
      wait_until_tor_is_working
      $vm.spawn("restart-vidalia")
    end
  else
    $vm.host_to_guest_time_sync
  end
end

Given /^a computer$/ do
  $vm.destroy_and_undefine if $vm
  $vm = VM.new($virt, VM_XML_PATH, $vmnet, $vmstorage, DISPLAY)
end

Given /^the computer has (\d+) ([[:alpha:]]+) of RAM$/ do |size, unit|
  $vm.set_ram_size(size, unit)
end

Given /^the computer is set to boot from the Tails DVD$/ do
  $vm.set_cdrom_boot(TAILS_ISO)
end

Given /^the computer is set to boot from (.+?) drive "(.+?)"$/ do |type, name|
  $vm.set_disk_boot(name, type.downcase)
end

Given /^I (temporarily )?create a (\d+) ([[:alpha:]]+) disk named "([^"]+)"$/ do |temporary, size, unit, name|
  $vm.storage.create_new_disk(name, {:size => size, :unit => unit,
                                     :type => "qcow2"})
  add_after_scenario_hook { $vm.storage.delete_volume(name) } if temporary
end

Given /^I plug (.+) drive "([^"]+)"$/ do |bus, name|
  $vm.plug_drive(name, bus.downcase)
  if $vm.is_running?
    step "drive \"#{name}\" is detected by Tails"
  end
end

Then /^drive "([^"]+)" is detected by Tails$/ do |name|
  if $vm.is_running?
    try_for(10, :msg => "Drive '#{name}' is not detected by Tails") {
      $vm.disk_detected?(name)
    }
  else
    STDERR.puts "Cannot tell if drive '#{name}' is detected by Tails: " +
                "Tails is not running"
  end
end

Given /^the network is plugged$/ do
  # We don't skip this step when restoring the background to ensure
  # that the network state is actually the same after restoring as
  # when the snapshot was made.
  $vm.plug_network
end

Given /^the network is unplugged$/ do
  # See comment in the step "the network is plugged".
  $vm.unplug_network
end

Given /^the hardware clock is set to "([^"]*)"$/ do |time|
  next if @skip_steps_while_restoring_background
  $vm.set_hardware_clock(DateTime.parse(time).to_time)
end

Given /^I capture all network traffic$/ do
  # Note: We don't want skip this particular stpe if
  # @skip_steps_while_restoring_background is set since it starts
  # something external to the VM state.
  @sniffer = Sniffer.new("sniffer", $vmnet)
  @sniffer.capture
  add_after_scenario_hook do
    @sniffer.stop
    @sniffer.clear
  end
end

Given /^I set Tails to boot with options "([^"]*)"$/ do |options|
  @boot_options = options
end

When /^I start the computer$/ do
  assert(!$vm.is_running?,
         "Trying to start a VM that is already running")
  $vm.start
  post_vm_start_hook
end

Given /^I start Tails( from DVD)?( with network unplugged)?( and I login)?$/ do |dvd_boot, network_unplugged, do_login|
  # we don't @skip_steps_while_restoring_background as we're only running
  # other steps, that are taking care of it *if* they have to
  step "the computer is set to boot from the Tails DVD" if dvd_boot
  if network_unplugged.nil?
    step "the network is plugged"
  else
    step "the network is unplugged"
  end
  step "I start the computer"
  step "the computer boots Tails"
  if do_login
    step "I log in to a new session"
    step "Tails seems to have booted normally"
    if network_unplugged.nil?
      step "Tor is ready"
      step "all notifications have disappeared"
      step "available upgrades have been checked"
    else
      step "all notifications have disappeared"
    end
  end
end

Given /^I start Tails from (.+?) drive "(.+?)"(| with network unplugged)( and I login(| with(| read-only) persistence enabled))?$/ do |drive_type, drive_name, network_unplugged, do_login, persistence_on, persistence_ro|
  # we don't @skip_steps_while_restoring_background as we're only running
  # other steps, that are taking care of it *if* they have to
  step "the computer is set to boot from #{drive_type} drive \"#{drive_name}\""
  if network_unplugged.empty?
    step "the network is plugged"
  else
    step "the network is unplugged"
  end
  step "I start the computer"
  step "the computer boots Tails"
  if do_login
    if ! persistence_on.empty?
      if persistence_ro.empty?
        step "I enable persistence"
      else
        step "I enable read-only persistence"
      end
    end
    step "I log in to a new session"
    step "Tails seems to have booted normally"
    if network_unplugged.empty?
      step "Tor is ready"
      step "all notifications have disappeared"
      step "available upgrades have been checked"
    else
      step "all notifications have disappeared"
    end
  end
end

When /^I power off the computer$/ do
  assert($vm.is_running?,
         "Trying to power off an already powered off VM")
  $vm.power_off
end

When /^I cold reboot the computer$/ do
  step "I power off the computer"
  step "I start the computer"
end

When /^I destroy the computer$/ do
  $vm.destroy_and_undefine
end

Given /^the computer (re)?boots Tails$/ do |reboot|

  boot_timeout = 30
  # We need some extra time for memory wiping if rebooting
  boot_timeout += 90 if reboot

  case @os_loader
  when "UEFI"
    bootsplash = 'TailsBootSplashUEFI.png'
    bootsplash_tab_msg = 'TailsBootSplashTabMsgUEFI.png'
  else
    bootsplash = 'TailsBootSplash.png'
    bootsplash_tab_msg = 'TailsBootSplashTabMsg.png'
  end

  @screen.wait(bootsplash, boot_timeout)
  @screen.wait(bootsplash_tab_msg, 10)
  @screen.type(Sikuli::Key.TAB)
  @screen.waitVanish(bootsplash_tab_msg, 1)

  @screen.type(" autotest_never_use_this_option blacklist=psmouse #{@boot_options}" +
               Sikuli::Key.ENTER)
  @screen.wait('TailsGreeter.png', 30*60)
  $vm.wait_until_remote_shell_is_up
  activate_filesystem_shares
end

Given /^I log in to a new session(?: in )?(|German)$/ do |lang|
  case lang
  when 'German'
    @language = "German"
    @screen.wait_and_click('TailsGreeterLanguage.png', 10)
    @screen.wait_and_click("TailsGreeterLanguage#{@language}.png", 10)
    @screen.wait_and_click("TailsGreeterLoginButton#{@language}.png", 10)
  when ''
    @screen.wait_and_click('TailsGreeterLoginButton.png', 10)
  else
    raise "Unsupported language: #{lang}"
  end
end

Given /^I enable more Tails Greeter options$/ do
  match = @screen.find('TailsGreeterMoreOptions.png')
  @screen.click(match.getCenter.offset(match.w/2, match.h*2))
  @screen.wait_and_click('TailsGreeterForward.png', 10)
  @screen.wait('TailsGreeterLoginButton.png', 20)
end

Given /^I enable the specific Tor configuration option$/ do
  @screen.click('TailsGreeterTorConf.png')
end

Given /^I set an administration password$/ do
  @screen.wait("TailsGreeterAdminPassword.png", 20)
  @screen.type(@sudo_password)
  @screen.type(Sikuli::Key.TAB)
  @screen.type(@sudo_password)
end

Given /^Tails Greeter has dealt with the sudo password$/ do
  f1 = "/etc/sudoers.d/tails-greeter"
  f2 = "#{f1}-no-password-lecture"
  try_for(20) {
    $vm.execute("test -e '#{f1}' -o -e '#{f2}'").success?
  }
end

Given /^the Tails desktop is ready$/ do
  case @theme
  when "windows"
    desktop_started_picture = 'WindowsStartButton.png'
  else
    desktop_started_picture = "GnomeApplicationsMenu#{@language}.png"
    # We wait for the Florence icon to be displayed to ensure reliable systray icon clicking.
    # By this point the only icon left is Vidalia and it will not cause the other systray
    # icons to shift positions.
    @screen.wait("GnomeSystrayFlorence.png", 180)
  end
  @screen.wait(desktop_started_picture, 180)
end

Then /^Tails seems to have booted normally$/ do
  step "the Tails desktop is ready"
end

When /^I see the 'Tor is ready' notification$/ do
  @screen.wait("GnomeTorIsReady.png", 300)
  @screen.waitVanish("GnomeTorIsReady.png", 15)
end

Given /^Tor is ready$/ do
  step "Tor has built a circuit"
  step "the time has synced"
end

Given /^Tor has built a circuit$/ do
  wait_until_tor_is_working
end

Given /^the time has synced$/ do
  ["/var/run/tordate/done", "/var/run/htpdate/success"].each do |file|
    try_for(300) { $vm.execute("test -e #{file}").success? }
  end
end

Given /^available upgrades have been checked$/ do
  try_for(300) {
    $vm.execute("test -e '/var/run/tails-upgrader/checked_upgrades'").success?
  }
end

Given /^the Tor Browser has started$/ do
  case @theme
  when "windows"
    tor_browser_picture = "WindowsTorBrowserWindow.png"
  else
    tor_browser_picture = "TorBrowserWindow.png"
  end

  @screen.wait(tor_browser_picture, 60)
end

Given /^the Tor Browser has started and loaded the (startup page|Tails roadmap)$/ do |page|
  case page
  when "startup page"
    picture = "TorBrowserStartupPage.png"
  when "Tails roadmap"
    picture = "TorBrowserTailsRoadmap.png"
  else
    raise "Unsupported page: #{page}"
  end
  step "the Tor Browser has started"
  @screen.wait(picture, 120)
end

Given /^the Tor Browser has started in offline mode$/ do
  @screen.wait("TorBrowserOffline.png", 60)
end

Given /^I add a bookmark to eff.org in the Tor Browser$/ do
  url = "https://www.eff.org"
  step "I open the address \"#{url}\" in the Tor Browser"
  @screen.wait("TorBrowserOffline.png", 5)
  @screen.type("d", Sikuli::KeyModifier.CTRL)
  @screen.wait("TorBrowserBookmarkPrompt.png", 10)
  @screen.type(url + Sikuli::Key.ENTER)
end

Given /^the Tor Browser has a bookmark to eff.org$/ do
  @screen.type("b", Sikuli::KeyModifier.ALT)
  @screen.wait("TorBrowserEFFBookmark.png", 10)
end

Given /^all notifications have disappeared$/ do
  case @theme
  when "windows"
    notification_picture = "WindowsNotificationX.png"
  else
    notification_picture = "GnomeNotificationX.png"
  end
  @screen.waitVanish(notification_picture, 60)
end

Then /^I see "([^"]*)" after at most (\d+) seconds$/ do |image, time|
  @screen.wait(image, time.to_i)
end

Then /^all Internet traffic has only flowed through Tor$/ do
  leaks = FirewallLeakCheck.new(@sniffer.pcap_file, get_all_tor_nodes)
  leaks.assert_no_leaks
end

Given /^I enter the sudo password in the gksu prompt$/ do
  @screen.wait('GksuAuthPrompt.png', 60)
  sleep 1 # wait for weird fade-in to unblock the "Ok" button
  @screen.type(@sudo_password)
  @screen.type(Sikuli::Key.ENTER)
  @screen.waitVanish('GksuAuthPrompt.png', 10)
end

Given /^I enter the sudo password in the pkexec prompt$/ do
  step "I enter the \"#{@sudo_password}\" password in the pkexec prompt"
end

def deal_with_polkit_prompt (image, password)
  @screen.wait(image, 60)
  @screen.type(password)
  @screen.type(Sikuli::Key.ENTER)
  @screen.waitVanish(image, 10)
end

Given /^I enter the "([^"]*)" password in the pkexec prompt$/ do |password|
  deal_with_polkit_prompt('PolicyKitAuthPrompt.png', password)
end

Given /^process "([^"]+)" is running$/ do |process|
  assert($vm.has_process?(process),
         "Process '#{process}' is not running")
end

Given /^process "([^"]+)" is running within (\d+) seconds$/ do |process, time|
  try_for(time.to_i, :msg => "Process '#{process}' is not running after " +
                             "waiting for #{time} seconds") do
    $vm.has_process?(process)
  end
end

Given /^process "([^"]+)" has stopped running after at most (\d+) seconds$/ do |process, time|
  try_for(time.to_i, :msg => "Process '#{process}' is still running after " +
                             "waiting for #{time} seconds") do
    not $vm.has_process?(process)
  end
end

Given /^process "([^"]+)" is not running$/ do |process|
  assert(!$vm.has_process?(process),
         "Process '#{process}' is running")
end

Given /^I kill the process "([^"]+)"$/ do |process|
  $vm.execute("killall #{process}")
  try_for(10, :msg => "Process '#{process}' could not be killed") {
    !$vm.has_process?(process)
  }
end

Then /^Tails eventually shuts down$/ do
  nr_gibs_of_ram = (detected_ram_in_MiB.to_f/(2**10)).ceil
  timeout = nr_gibs_of_ram*5*60
  try_for(timeout, :msg => "VM is still running after #{timeout} seconds") do
    ! $vm.is_running?
  end
end

Then /^Tails eventually restarts$/ do
  nr_gibs_of_ram = (detected_ram_in_MiB.to_f/(2**10)).ceil
  @screen.wait('TailsBootSplash.png', nr_gibs_of_ram*5*60)
end

Given /^I shutdown Tails and wait for the computer to power off$/ do
  $vm.execute("poweroff")
  step 'Tails eventually shuts down'
end

When /^I request a shutdown using the emergency shutdown applet$/ do
  @screen.hide_cursor
  @screen.wait_and_click('TailsEmergencyShutdownButton.png', 10)
  @screen.hide_cursor
  @screen.wait_and_click('TailsEmergencyShutdownHalt.png', 10)
end

When /^I warm reboot the computer$/ do
  $vm.execute("reboot")
end

When /^I request a reboot using the emergency shutdown applet$/ do
  @screen.hide_cursor
  @screen.wait_and_click('TailsEmergencyShutdownButton.png', 10)
  @screen.hide_cursor
  @screen.wait_and_click('TailsEmergencyShutdownReboot.png', 10)
end

Given /^package "([^"]+)" is installed$/ do |package|
  assert($vm.execute("dpkg -s '#{package}' 2>/dev/null | grep -qs '^Status:.*installed$'").success?,
         "Package '#{package}' is not installed")
end

When /^I start the Tor Browser$/ do
  step 'I start "TorBrowser" via the GNOME "Internet" applications menu'
end

When /^I start the Tor Browser in offline mode$/ do
  step "I start the Tor Browser"
  case @theme
  when "windows"
    @screen.wait_and_click("WindowsTorBrowserOfflinePrompt.png", 10)
    @screen.click("WindowsTorBrowserOfflinePromptStart.png")
  else
    @screen.wait_and_click("TorBrowserOfflinePrompt.png", 10)
    @screen.click("TorBrowserOfflinePromptStart.png")
  end
end

def xul_application_info(application)
  binary = $vm.execute_successfully(
                '. /usr/local/lib/tails-shell-library/tor-browser.sh; ' +
                'echo ${TBB_INSTALL}/firefox'
                                    ).stdout.chomp
  case application
  when "Tor Browser"
    user = LIVE_USER
    cmd_regex = "#{binary} .* -profile /home/#{user}/\.tor-browser/profile\.default"
    chroot = ""
    new_tab_button_image = "TorBrowserNewTabButton.png"
    address_bar_image = "TorBrowserAddressBar.png"
  when "Unsafe Browser"
    user = "clearnet"
    cmd_regex = "#{binary} .* -profile /home/#{user}/\.unsafe-browser/profile\.default"
    chroot = "/var/lib/unsafe-browser/chroot"
    new_tab_button_image = "UnsafeBrowserNewTabButton.png"
    address_bar_image = "UnsafeBrowserAddressBar.png"
  when "I2P Browser"
    user = "i2pbrowser"
    cmd_regex = "#{binary} .* -profile /home/#{user}/\.i2p-browser/profile\.default"
    chroot = "/var/lib/i2p-browser/chroot"
    new_tab_button_image = nil
    address_bar_image = nil
  when "Tor Launcher"
    user = "tor-launcher"
    cmd_regex = "#{binary} -app /home/#{user}/\.tor-launcher/tor-launcher-standalone/application\.ini"
    chroot = ""
    new_tab_button_image = nil
    address_bar_image = nil
  else
    raise "Invalid browser or XUL application: #{application}"
  end
  return {
    :user => user,
    :cmd_regex => cmd_regex,
    :chroot => chroot,
    :new_tab_button_image => new_tab_button_image,
    :address_bar_image => address_bar_image,
  }
end

When /^I open a new tab in the (.*)$/ do |browser|
  info = xul_application_info(browser)
  @screen.click(info[:new_tab_button_image])
  @screen.wait(info[:address_bar_image], 10)
end

When /^I open the address "([^"]*)" in the (.*)$/ do |address, browser|
  step "I open a new tab in the #{browser}"
  info = xul_application_info(browser)
  @screen.click(info[:address_bar_image])
  sleep 0.5
  @screen.type(address + Sikuli::Key.ENTER)
end

Then /^the (.*) has no plugins installed$/ do |browser|
  step "I open the address \"about:plugins\" in the #{browser}"
  step "I see \"TorBrowserNoPlugins.png\" after at most 30 seconds"
end

def xul_app_shared_lib_check(pid, chroot)
  expected_absent_tbb_libs = ['libnssdbm3.so']
  absent_tbb_libs = []
  unwanted_native_libs = []
  tbb_libs = $vm.execute_successfully(
                 ". /usr/local/lib/tails-shell-library/tor-browser.sh; " +
                 "ls -1 #{chroot}${TBB_INSTALL}/*.so"
                                      ).stdout.split
  firefox_pmap_info = $vm.execute("pmap #{pid}").stdout
  for lib in tbb_libs do
    lib_name = File.basename lib
    if not /\W#{lib}$/.match firefox_pmap_info
      absent_tbb_libs << lib_name
    end
    native_libs = $vm.execute_successfully(
                       "find /usr/lib /lib -name \"#{lib_name}\""
                                           ).stdout.split
    for native_lib in native_libs do
      if /\W#{native_lib}$"/.match firefox_pmap_info
        unwanted_native_libs << lib_name
      end
    end
  end
  absent_tbb_libs -= expected_absent_tbb_libs
  assert(absent_tbb_libs.empty? && unwanted_native_libs.empty?,
         "The loaded shared libraries for the firefox process are not the " +
         "way we expect them.\n" +
         "Expected TBB libs that are absent: #{absent_tbb_libs}\n" +
         "Native libs that we don't want: #{unwanted_native_libs}")
end

Then /^the (.*) uses all expected TBB shared libraries$/ do |application|
  info = xul_application_info(application)
  pid = $vm.execute_successfully("pgrep --uid #{info[:user]} --full --exact '#{info[:cmd_regex]}'").stdout.chomp
  assert(/\A\d+\z/.match(pid), "It seems like #{application} is not running")
  xul_app_shared_lib_check(pid, info[:chroot])
end

Then /^the (.*) chroot is torn down$/ do |browser|
  info = xul_application_info(browser)
  try_for(30, :msg => "The #{browser} chroot '#{info[:chroot]}' was " \
                      "not removed") do
    !$vm.execute("test -d '#{info[:chroot]}'").success?
  end
end

Then /^the (.*) runs as the expected user$/ do |browser|
  info = xul_application_info(browser)
  assert_vmcommand_success($vm.execute(
    "pgrep --full --exact '#{info[:cmd_regex]}'"),
    "The #{browser} is not running")
  assert_vmcommand_success($vm.execute(
    "pgrep --uid #{info[:user]} --full --exact '#{info[:cmd_regex]}'"),
    "The #{browser} is not running as the #{info[:user]} user")
end

Given /^I add a wired DHCP NetworkManager connection called "([^"]+)"$/ do |con_name|
  con_content = <<EOF
[802-3-ethernet]
duplex=full

[connection]
id=#{con_name}
uuid=bbc60668-1be0-11e4-a9c6-2f1ce0e75bf1
type=802-3-ethernet
timestamp=1395406011

[ipv6]
method=auto

[ipv4]
method=auto
EOF
  con_content.split("\n").each do |line|
    $vm.execute("echo '#{line}' >> /tmp/NM.#{con_name}")
  end
  $vm.execute("install -m 0600 '/tmp/NM.#{con_name}' '/etc/NetworkManager/system-connections/#{con_name}'")
  try_for(10) {
    nm_con_list = $vm.execute("nmcli --terse --fields NAME con list").stdout
    nm_con_list.split("\n").include? "#{con_name}"
  }
end

Given /^I switch to the "([^"]+)" NetworkManager connection$/ do |con_name|
  $vm.execute("nmcli con up id #{con_name}")
  try_for(60) {
    $vm.execute("nmcli --terse --fields NAME,STATE con status").stdout.chomp == "#{con_name}:activated"
  }
end

When /^I start and focus GNOME Terminal$/ do
  step 'I start "Terminal" via the GNOME "Accessories" applications menu'
  @screen.wait_and_click('GnomeTerminalWindow.png', 20)
end

When /^I run "([^"]+)" in GNOME Terminal$/ do |command|
  if !$vm.has_process?("gnome-terminal")
    step "I start and focus GNOME Terminal"
  else
    @screen.wait_and_click('GnomeTerminalWindow.png', 20)
  end
  @screen.type(command + Sikuli::Key.ENTER)
end

When /^the file "([^"]+)" exists(?:| after at most (\d+) seconds)$/ do |file, timeout|
  timeout = 0 if timeout.nil?
  try_for(
    timeout.to_i,
    :msg => "The file #{file} does not exist after #{timeout} seconds"
  ) {
    $vm.file_exist?(file)
  }
end

When /^the file "([^"]+)" does not exist$/ do |file|
  assert(! ($vm.file_exist?(file)))
end

When /^the directory "([^"]+)" exists$/ do |directory|
  assert($vm.directory_exist?(directory))
end

When /^the directory "([^"]+)" does not exist$/ do |directory|
  assert(! ($vm.directory_exist?(directory)))
end

When /^I copy "([^"]+)" to "([^"]+)" as user "([^"]+)"$/ do |source, destination, user|
  c = $vm.execute("cp \"#{source}\" \"#{destination}\"", LIVE_USER)
  assert(c.success?, "Failed to copy file:\n#{c.stdout}\n#{c.stderr}")
end

def is_persistent?(app)
  conf = get_persistence_presets(true)["#{app}"]
  $vm.execute("findmnt --noheadings --output SOURCE --target '#{conf}'").success?
end

Then /^persistence for "([^"]+)" is (|not )enabled$/ do |app, enabled|
  case enabled
  when ''
    assert(is_persistent?(app), "Persistence should be enabled.")
  when 'not '
    assert(!is_persistent?(app), "Persistence should not be enabled.")
  end
end

def gnome_app_menu_click_helper(click_me, verify_me = nil)
  try_for(30) do
    @screen.hide_cursor
    @screen.wait_and_click(click_me, 10)
    @screen.wait(verify_me, 10) if verify_me
    return
  end
end

Given /^I start "([^"]+)" via the GNOME "([^"]+)" applications menu$/ do |app, submenu|
  case @theme
  when "windows"
    prefix = 'Windows'
  else
    prefix = 'Gnome'
  end
  menu_button = prefix + "ApplicationsMenu.png"
  sub_menu_entry = prefix + "Applications" + submenu + ".png"
  application_entry = prefix + "Applications" + app + ".png"
  try_for(120) do
    begin
      gnome_app_menu_click_helper(menu_button, sub_menu_entry)
      gnome_app_menu_click_helper(sub_menu_entry, application_entry)
      gnome_app_menu_click_helper(application_entry)
    rescue Exception => e
      # Close menu, if still open
      @screen.type(Sikuli::Key.ESC)
      raise e
    end
    true
  end
end

Given /^I start "([^"]+)" via the GNOME "([^"]+)"\/"([^"]+)" applications menu$/ do |app, submenu, subsubmenu|
  case @theme
  when "windows"
    prefix = 'Windows'
  else
    prefix = 'Gnome'
  end
  menu_button = prefix + "ApplicationsMenu.png"
  sub_menu_entry = prefix + "Applications" + submenu + ".png"
  sub_sub_menu_entry = prefix + "Applications" + subsubmenu + ".png"
  application_entry = prefix + "Applications" + app + ".png"
  try_for(120) do
    begin
      gnome_app_menu_click_helper(menu_button, sub_menu_entry)
      gnome_app_menu_click_helper(sub_menu_entry, sub_sub_menu_entry)
      gnome_app_menu_click_helper(sub_sub_menu_entry, application_entry)
      gnome_app_menu_click_helper(application_entry)
    rescue Exception => e
      # Close menu, if still open
      @screen.type(Sikuli::Key.ESC)
      raise e
    end
    true
  end
end

When /^I type "([^"]+)"$/ do |string|
  @screen.type(string)
end

When /^I press the "([^"]+)" key$/ do |key|
  begin
    @screen.type(eval("Sikuli::Key.#{key}"))
  rescue RuntimeError
    raise "unsupported key #{key}"
  end
end

Then /^the (amnesiac|persistent) Tor Browser directory (exists|does not exist)$/ do |persistent_or_not, mode|
  case persistent_or_not
  when "amnesiac"
    dir = "/home/#{LIVE_USER}/Tor Browser"
  when "persistent"
    dir = "/home/#{LIVE_USER}/Persistent/Tor Browser"
  end
  step "the directory \"#{dir}\" #{mode}"
end

Then /^there is a GNOME bookmark for the (amnesiac|persistent) Tor Browser directory$/ do |persistent_or_not|
  case persistent_or_not
  when "amnesiac"
    bookmark_image = 'TorBrowserAmnesicFilesBookmark.png'
  when "persistent"
    bookmark_image = 'TorBrowserPersistentFilesBookmark.png'
  end
  @screen.wait_and_click('GnomePlaces.png', 10)
  @screen.wait(bookmark_image, 40)
  @screen.type(Sikuli::Key.ESC)
end

Then /^there is no GNOME bookmark for the persistent Tor Browser directory$/ do
  try_for(65) do
    @screen.wait_and_click('GnomePlaces.png', 10)
    @screen.wait("GnomePlacesWithoutTorBrowserPersistent.png", 10)
    @screen.type(Sikuli::Key.ESC)
  end
end

def pulseaudio_sink_inputs
  pa_info = $vm.execute_successfully('pacmd info', LIVE_USER).stdout
  sink_inputs_line = pa_info.match(/^\d+ sink input\(s\) available\.$/)[0]
  return sink_inputs_line.match(/^\d+/)[0].to_i
end

When /^(no|\d+) application(?:s?) (?:is|are) playing audio(?:| after (\d+) seconds)$/ do |nb, wait_time|
  nb = 0 if nb == "no"
  sleep wait_time.to_i if ! wait_time.nil?
  assert_equal(nb.to_i, pulseaudio_sink_inputs)
end

When /^I double-click on the "Tails documentation" link on the Desktop$/ do
  @screen.wait_and_double_click("DesktopTailsDocumentationIcon.png", 10)
end

When /^I click the blocked video icon$/ do
  @screen.wait_and_click("TorBrowserBlockedVideo.png", 30)
end

When /^I accept to temporarily allow playing this video$/ do
  @screen.wait_and_click("TorBrowserOkButton.png", 10)
end

When /^I click the HTML5 play button$/ do
  @screen.wait_and_click("TorBrowserHtml5PlayButton.png", 30)
end

When /^I can save the current page as "([^"]+[.]html)" to the (default downloads|persistent Tor Browser) directory$/ do |output_file, output_dir|
  @screen.type("s", Sikuli::KeyModifier.CTRL)
  if output_dir == "persistent Tor Browser"
    output_dir = "/home/#{LIVE_USER}/Persistent/Tor Browser"
    @screen.wait_and_click("GtkTorBrowserPersistentBookmark.png", 10)
    @screen.wait("GtkTorBrowserPersistentBookmarkSelected.png", 10)
    # The output filename (without its extension) is already selected,
    # let's use the keyboard shortcut to focus its field
    @screen.type("n", Sikuli::KeyModifier.ALT)
    @screen.wait("TorBrowserSaveOutputFileSelected.png", 10)
  else
    output_dir = "/home/#{LIVE_USER}/Tor Browser"
  end
  # Only the part of the filename before the .html extension can be easily replaced
  # so we have to remove it before typing it into the arget filename entry widget.
  @screen.type(output_file.sub(/[.]html$/, ''))
  @screen.type(Sikuli::Key.ENTER)
  try_for(10, :msg => "The page was not saved to #{output_dir}/#{output_file}") {
    $vm.file_exist?("#{output_dir}/#{output_file}")
  }
end

When /^I can print the current page as "([^"]+[.]pdf)" to the (default downloads|persistent Tor Browser) directory$/ do |output_file, output_dir|
  if output_dir == "persistent Tor Browser"
    output_dir = "/home/#{LIVE_USER}/Persistent/Tor Browser"
  else
    output_dir = "/home/#{LIVE_USER}/Tor Browser"
  end
  @screen.type("p", Sikuli::KeyModifier.CTRL)
  @screen.wait("TorBrowserPrintDialog.png", 10)
  @screen.wait_and_click("PrintToFile.png", 10)
  # Tor Browser is not allowed to read /home/#{LIVE_USER}, and I found no way
  # to change the default destination directory for "Print to File",
  # so let's click through the warning
  @screen.wait("TorBrowserCouldNotReadTheContentsOfWarning.png", 10)
  @screen.wait_and_click("TorBrowserWarningDialogOkButton.png", 10)
  @screen.wait_and_double_click("TorBrowserPrintOutputFile.png", 10)
  @screen.hide_cursor
  @screen.wait("TorBrowserPrintOutputFileSelected.png", 10)
  # Only the file's basename is selected by double-clicking,
  # so we type only the desired file's basename to replace it
  @screen.type(output_dir + '/' + output_file.sub(/[.]pdf$/, '') + Sikuli::Key.ENTER)
  try_for(30, :msg => "The page was not printed to #{output_dir}/#{output_file}") {
    $vm.file_exist?("#{output_dir}/#{output_file}")
  }
end

When /^I accept to import the key with Seahorse$/ do
  @screen.wait_and_click("TorBrowserOkButton.png", 10)
end
