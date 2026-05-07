follow https://flywheel-io.gitlab.io/tools/app/cli/fw-beta/#:~:text=Data%20Platform.-,Installing%20locally,-The%20stable%20version to install flywheel CLI

docker build -t xx ./

docker push xx

fw-beta gear build .

fw-beta login

Flywheel API key: 
fw-beta gear upload
