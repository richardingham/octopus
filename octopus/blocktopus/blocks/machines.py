# Package Imports
from ..workspace import Block, Disconnected, Cancelled

# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.python import log

# Octopus Imports
from octopus import data
from octopus.constants import State
import octopus.transport.basic


class connection_declaration (Block):
	pass


class machine_declaration (Block):
	def _varName (self, name = None):
		return "global.machine::" + (name or self.fields['NAME'])

	def created (self):
		@self.on('value-changed')
		def onVarNameChanged (data):
			if not (data["block"] is self and data["field"] == 'NAME'):
				return

			self.workspace.variables.rename(data["oldValue"], data["newValue"])

	def _run (self):
		@defer.inlineCallbacks
		def _connect ():
			connection = yield self.getInputValue('CONNECTION', None)

			if connection is None:
				raise Exception("No connection specified for machine '{:s}'".format(self.fields['NAME']))

			cls = self.getMachineClass()
			self.machine = cls(
				connection,
				alias = self.fields['NAME'],
				**self.getMachineParams()
			)
			self.workspace.variables.add(self._varName(), self.machine)

			try:
				result = yield self.machine.ready
			except Exception as e:
				print ("Machine connection error: " + str(e))
				raise e

			print ("Machine block: connection complete to " + str(self.machine))

			self.workspace.on("workspace-stopped", self._onWorkspaceStopped)
			self.workspace.on("workspace-paused", self._onWorkspacePaused)
			self.workspace.on("workspace-resumed", self._onWorkspaceResumed)

			# Short delay to allow the machine to get its first data
			# TODO - machines should only return ready when they
			# have received their first data.
			# TODO - make reset configurable.
			yield defer.gatherResults([
				task.deferLater(reactor, 2, lambda: result),
				self.machine.reset()
			])

		return _connect()

	def _onWorkspaceStopped (self, data):
		print ("Machine block: terminating connection to " + str(self.machine))

		self.workspace.off("workspace-stopped", self._onWorkspaceStopped)
		self.workspace.off("workspace-paused", self._onWorkspacePaused)
		self.workspace.off("workspace-resumed", self._onWorkspaceResumed)

		self.machine.stop()
		self.workspace.variables.remove(self._varName())

		def _disconnect (machine):
			try:
				machine.disconnect()
			except AttributeError:
				pass
			except:
				log.err()

		# Allow some time for any remaining messages to be received.
		reactor.callLater(2, _disconnect, self.machine)
		self.machine = None

	def _onWorkspacePaused (self, data):
		self.machine.pause()

	def _onWorkspaceResumed (self, data):
		self.machine.resume()

	def getMachineClass (self):
		raise NotImplementedError()
		
	def getMachineParams (self):
		return {}

	def getGlobalDeclarationNames (self):
		name = self._varName()

		return Block.getGlobalDeclarationNames(self,
			[name] if not self.disabled else []
		)


class machine_knauer_K120 (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import knauer
		return knauer.K120


class machine_knauer_S100 (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import knauer
		return knauer.S100


class machine_vici_multivalve (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import vici
		return vici.MultiValve


class machine_mt_icir (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import mt
		return mt.ICIR

	def getMachineParams (self):
		import json
		try:
			return {
				"stream_names": json.loads(self.mutation)['stream_names']
			}
		except (ValueError, KeyError):
			return {}


class machine_wpi_aladdin (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import wpi
		return wpi.Aladdin

	def getMachineParams (self):
		import json
		try:
			return {
				"syringe_diameter": int(json.loads(self.mutation)['syringe_diameter'])
			}
		except (ValueError, KeyError):
			return {}


class machine_phidgets_phsensor (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import phidgets
		return phidgets.PHSensor

	def getMachineParams (self):
		import json
		try:
			return {
				"min_change": float(json.loads(self.mutation)['min_change'])
			}
		except (ValueError, KeyError):
			return {}


class machine_omega_hh306a (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import omega
		return omega.HH306A


class machine_harvard_phd2000 (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import harvard
		return harvard.PHD2000Infuser

	def getMachineParams (self):
		import json
		try:
			return {
				"syringe_diameter": int(json.loads(self.mutation)['syringe_diameter'])
			}
		except (ValueError, KeyError):
			return {}


class machine_mt_sics_balance (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import mt
		return mt.SICSBalance


class machine_startech_powerremotecontrol (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import startech
		return startech.PowerRemoteControl


class machine_gilson_FractionCollector203B (machine_declaration):
	def getMachineClass (self):
		from octopus.manufacturer import gilson
		return gilson.FractionCollector203B


class connection_tcp (connection_declaration):
	def eval (self):
		return defer.succeed(octopus.transport.basic.tcp(
			str(self.fields['HOST']),
			int(self.fields['PORT'])
		))


class connection_serial (connection_declaration):
	def eval (self):
		return defer.succeed(octopus.transport.basic.serial(
			str(self.fields['PORT']),
			baudrate = int(self.fields['BAUD'])
		))


class connection_phidget (connection_declaration):
	def eval (self):
		from octopus.transport.phidgets import Phidget
		return defer.succeed(Phidget(
			int(self.fields['ID']),
		))
