follow https://flywheel-io.gitlab.io/tools/app/cli/fw-beta/#:~:text=Data%20Platform.-,Installing%20locally,-The%20stable%20version to install flywheel CLI

docker build -t difan0224/lisa:0.4.0 ./

docker push difan0224/lisa:0.4.0

fw-beta gear build .

fw-beta login

Flywheel API key: bmgf.flywheel.io:djE4hU5dxd1S2n9YhJYF2mkikW1WNmwMMIq845fedLFKTWiHYaVAXCzag

fw-beta gear upload
