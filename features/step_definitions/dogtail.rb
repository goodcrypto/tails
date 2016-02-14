When /^I enable the accessibility toolkit in GNOME$/ do
  $vm.execute_successfully(
    'gsettings set org.gnome.desktop.interface toolkit-accessibility true',
    :user => LIVE_USER,
  )
end

When /^I start gedit$/ do
  step 'I start "Gedit" via the GNOME "Accessories" applications menu'
  @screen.wait_and_click("GeditWindow.png", 20)
  # We don't have a good visual indicator for when we can continue. Without the
  # sleep we may start typing in the gedit window far too soon, causing
  # keystrokes to go missing.
  sleep 5
end

Then /^dogtail works$/ do
  $vm.file_append(
    '/tmp/dogtail_test.py',
    File.open('features/scripts/dogtail_test.py').read
  )
  $vm.execute_successfully(
    'python /tmp/dogtail_test.py',
    :user => LIVE_USER,
  )
end
