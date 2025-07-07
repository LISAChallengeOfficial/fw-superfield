follow https://flywheel-io.gitlab.io/tools/app/cli/fw-beta/#:~:text=Data%20Platform.-,Installing%20locally,-The%20stable%20version to install flywheel CLI

docker build -t difan0224/superfield:0.1.0 ./

docker push difan0224/superfield:0.1.0

fw-beta gear build .

fw-beta login

Flywheel API key: 

fw-beta gear upload
