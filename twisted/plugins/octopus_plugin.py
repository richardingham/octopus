from twisted.application.service import ServiceMaker

octopus = ServiceMaker(
    name = 'octopus', 
	module = 'octopus.server.tap', 
	description = 'Run the octopus service.', 
	tapname = 'octopus'
)
