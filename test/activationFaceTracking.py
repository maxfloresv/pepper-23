#!/usr/bin/env python
import rospy
import smach
import smach_ros
from std_msgs.msg import String
from smach_ros import IntrospectionServer
from std_msgs.msg import String
from maqui_skills import robot_factory
from uchile_states.interaction.states import SpeakGestures, Speak, Hear, Tell, NoiseCheck
from uchile_states.head.states import StartFaceTracking
from uchile_states.perception import wait_face_detection
import speech_recognition as sr

# Define el estado "WaitForMakiState" que espera a que se publique "Maki" en el topico "/phrase"
class WaitForMakiState(smach.State):
	def __init__(self):
		smach.State.__init__(self, outcomes=['success', 'failure'], input_keys=['input_string'])
		self.robot = robot

	def execute(self, userdata):
		FaceTracking = StartFaceTracking(self.robot)
		status = FaceTracking.execute(userdata)

		print(status)

		rospy.loginfo('Esperando el string...')
		input_string = rospy.wait_for_message('phrase', String)
		input_string = str(input_string)
		rospy.loginfo('Procesando el string: %s', input_string)

		if 'Maki' in input_string or status == 'succeeded':
		    	return 'success'
		else:
		    	return 'failure'

class Speech(smach.State):
	def __init__(self):
		smach.State.__init__(self, outcomes=['success', 'failure'], input_keys=['input_string'])
		# Instancia principal
		self.r = sr.Recognizer()

	def execute(self, userdata):
		rospy.loginfo('Hablale a Popper...')

		# Ejecutar el microfono solo si no esta activo (evita lag)
		if not active:
			active = True
			with sr.Microphone() as source:
				# Escuchar instrucciones por 1.5 segundos
				audio = self.r.listen(source, None, 1.5)

				msg = String()

				with self.r.recognize_google(audio, language='es-ES') as data:
					msg.data = data

				# Acá ya habrá terminado de procesar la instrucción
				active = False

		# La idea es implementar un nodo de speech recognition con el código de arriba
#		input_string = rospy.wait_for_message('phrase', String)
#		input_string = str(input_string)
#		rospy.loginfo('Te escuche: %s', input_string)

		# Un buen indicador para ver si se recibió texto es que no esté vacío
		if len(input_string) > 0:
			return 'success'
		else:
			return 'failure'

# Define la state machine
def getInstance(robot):
    	sm = smach.StateMachine(outcomes=['succeeded', 'failure'])

	# Definir los estados y transiciones (Upd: Transito en statemachines, ok)
	with sm:
		# Empezamos el face tracking
		smach.StateMachine.add('StartFaceTracking', StartFaceTracking(robot), 
			transitions={
				'succeeded': 'DETECT_PERSON', 
			})
		
		smach.StateMachine.add('DETECT_PERSON', wait_face_detection.getInstance(robot, face_size=60, timeout=15),
			transitions={
				'succeeded' :'SpeechRecognition',
				'aborted'   :'StartFaceTracking',
				'preempted' :'StartFaceTracking' 
			}) 

		smach.StateMachine.add("SpeechRecognition", Speech(), 
			transitions={
				'success':'SpeechRecognition',
				'failure':'StartFaceTracking'
			})

		return sm

if __name__ == '__main__':
	rospy.init_node('RECEPTIONIST')
	base_skills = [ 
		"audition",
		"marker",
		"tablet",
		"tabletapp",
		"person_detector",
		"facial_features",
		"behavior_manager",
		"track_person"
	]

	extra_skills = ["tts"]
	robot = robot_factory.build(base_skills + extra_skills, core=True)

	sm = getInstance(robot)
	sis = IntrospectionServer('receptionist_introduce_guest', sm, '/INTRODUCE_GUEST_SM')
	sis.start()
	outcome = sm.execute()
	sis.stop()
