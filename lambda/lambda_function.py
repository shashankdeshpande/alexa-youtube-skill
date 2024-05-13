# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import os
import requests
import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_s3.adapter import S3Adapter 
s3_adapter = S3Adapter(bucket_name=os.environ["S3_PERSISTENCE_BUCKET"])

# from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.api_client import DefaultApiClient

from ask_sdk_core.dispatch_components import AbstractExceptionHandler, AbstractRequestHandler, AbstractRequestInterceptor, AbstractResponseInterceptor
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective, PlayBehavior, AudioItem, Stream, AudioItemMetadata,
    StopDirective, ClearQueueDirective, ClearBehavior)

from ask_sdk_model.services.directive import SendDirectiveRequest, Header, SpeakDirective
from ask_sdk_model.ui import StandardCard, Image

from ask_sdk_model import Response
import constants
import youtube

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_progressive_response(handler_input, intermediate_response):
    request_id_holder = handler_input.request_envelope.request.request_id
    directive_header = Header(request_id=request_id_holder)
    speech = SpeakDirective(speech=intermediate_response)
    directive_request = SendDirectiveRequest(
        header=directive_header, directive=speech)

    directive_service_client = handler_input.service_client_factory.get_directive_service()
    directive_service_client.enqueue(directive_request)

def check_if_url_exists(url):
    response = requests.head(url)
    return response.status_code == 200

def play(song_info, handler_input):
    logger.info("Song Info - {}".format(song_info))

    handler_input.response_builder.set_card(
        StandardCard(
            title=song_info["name"],
            text=song_info["title"],
            image=Image(
                small_image_url=song_info["thumbnail"],
                large_image_url=song_info["thumbnail"]
            )
        )
    )

    if check_if_url_exists(song_info["url"]):
        playback_info = handler_input.attributes_manager.persistent_attributes
        if 'info_dict' not in playback_info:
            playback_info['info_dict'] = {}
        playback_info['info_dict'][song_info['id']] = song_info
        handler_input.attributes_manager.persistent_attributes = playback_info
        handler_input.attributes_manager.save_persistent_attributes()
        
        handler_input.response_builder.add_directive(
            PlayDirective(
                play_behavior=PlayBehavior.REPLACE_ALL,
                audio_item=AudioItem(
                    stream=Stream(
                        token=song_info["id"],
                        url=song_info["url"],
                        offset_in_milliseconds=song_info.get('current_offset_in_milliseconds',0),
                        expected_previous_token=None),
                    metadata=None
                )
            )
        )
    else:
        handler_input.response_builder.speak(constants.INVALID_URL_MSG)
    return handler_input.response_builder.response

def add_song_in_queue(song_info, prev_song_info, handler_input):
    if check_if_url_exists(song_info["url"]):
        handler_input.response_builder.add_directive(
            PlayDirective(
                play_behavior=PlayBehavior.ENQUEUE,
                audio_item=AudioItem(
                    stream=Stream(
                        token=song_info["id"],
                        url=song_info["url"],
                        offset_in_milliseconds=0,
                        expected_previous_token=prev_song_info['id']),
                    metadata=None
                )
            )
        )
    return handler_input.response_builder.response

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = constants.WELCOME_MSG

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class PlayAudioHandler(AbstractRequestHandler):
    
    """Handler for PlayAudio intent."""
    
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("PlayAudioIntent")(handler_input)

    def handle(self, handler_input):
        query = handler_input.request_envelope.request.intent.slots["query"].value.lower()
        logger.info("In PlayAudioHandler")

        # progress response
        get_progressive_response(handler_input, constants.PROGRESS_MSG)
        song_info = youtube.search_ddgs(query)
        handler_input.response_builder.speak(constants.NOW_PLAYING_MSG.format(song_info['name']))
        return play(song_info, handler_input)

class PauseIntentHandler(AbstractRequestHandler):
    """Handler for Pause Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ((ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)
                     or ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input)
                     or ask_utils.is_intent_name("AMAZON.PauseIntent")(handler_input)))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("PausePlaybackHandler")
        handler_input.response_builder.add_directive(StopDirective())
        return handler_input.response_builder.response

class ResumeIntentHandler(AbstractRequestHandler):
    """Handler for Resume Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.ResumeIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("ResumeIntent")
        playback_info = handler_input.attributes_manager.persistent_attributes
        song_info = playback_info['current_song']
        return play(song_info, handler_input)

class PlayNextIntentHandler(AbstractRequestHandler):
    """Handler for Next Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.NextIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlayNextIntentHandler")
        playback_info = handler_input.attributes_manager.persistent_attributes
        logger.info('NEXT - {}'.format(playback_info))

        current_song_info = playback_info.get('current_song')
        if current_song_info:
            current_song_id = playback_info['current_song']['id']
            current_song_index = 0

            if current_song_id in playback_info.get('history', []):
                current_song_index = playback_info['history'].index(current_song_id)

            if (current_song_index+1) < len(playback_info.get('history',[])):
                next_song_id = playback_info['history'][current_song_index+1]
                next_song_info = playback_info['info_dict'][next_song_id]
            else:
                # progress response
                get_progressive_response(handler_input, "Exploring")
                next_song_info = youtube.get_suggested_video_info(current_song_id)

            handler_input.response_builder.speak(constants.NOW_PLAYING_MSG.format(next_song_info['name']))
            return play(next_song_info, handler_input)
        else:
            speak_output = constants.NEXT_SONG_FALLBACK_MSG
            return handler_input.response_builder.speak(speak_output).ask(speak_output).response

class PlayPreviousIntentHandler(AbstractRequestHandler):
    """Handler for Previous Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.PreviousIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlayPreviousIntentHandler")
        playback_info = handler_input.attributes_manager.persistent_attributes
        logger.info('PREVIOUS - {}'.format(playback_info))
        current_song_index = 0
        current_song_id = playback_info.get('current_song',{}).get('id')
        if current_song_id in playback_info.get('history',[]):
            current_song_index = playback_info['history'].index(current_song_id)

        if current_song_index >= 1:
            previous_song_id = playback_info['history'][current_song_index-1]
            previous_song_info = playback_info['info_dict'][previous_song_id]
            handler_input.response_builder.speak(constants.NOW_PLAYING_MSG.format(previous_song_info['name']))
            return play(previous_song_info, handler_input)
        else:
            speak_output = constants.PREVIOUS_SONG_FALLBACK_MSG
            return handler_input.response_builder.speak(speak_output).ask(speak_output).response


class PlaybackStartedEventHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackStarted Directive received.

    Confirming that the requested audio file began playing.
    Do not send any specific response.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackStarted")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackStartedHandler")
        
        song_id = handler_input.request_envelope.request.token
        playback_info = handler_input.attributes_manager.persistent_attributes
        song_info = playback_info['info_dict'][song_id]
        song_info.pop('current_offset_in_milliseconds', None)  # ignore offset 
        
        playback_info['current_song'] = song_info

        if 'history' not in playback_info:
            playback_info['history'] = []
        if 'info_dict' not in playback_info:
            playback_info['info_dict'] = {}
        
        if song_info['id'] not in playback_info['history']:
            playback_info['history'].append(song_info['id'])
            playback_info['info_dict'][song_info['id']] = song_info

        handler_input.attributes_manager.persistent_attributes = playback_info
        handler_input.attributes_manager.save_persistent_attributes()
        logger.info("Attributes - {}".format(playback_info))
        return handler_input.response_builder.response


class PlaybackFinishedEventHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFinished Directive received.

    Confirming that the requested audio file finished playing.
    Do not send any specific response.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackFinished")
        return handler_input.response_builder.response

class PlaybackNearlyFinishedEventHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackNearlyFinished Directive received.

    Replacing queue with the URL again. This should not happen on live streams.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackNearlyFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackNearlyFinishedHandler")
        playback_info = handler_input.attributes_manager.persistent_attributes
        current_song_info = playback_info['current_song']
        current_song_id = current_song_info['id']

        next_song_info = youtube.get_suggested_video_info(current_song_id)

        playback_info['info_dict'][next_song_info['id']] = next_song_info
        handler_input.attributes_manager.persistent_attributes = playback_info
        handler_input.attributes_manager.save_persistent_attributes()

        return add_song_in_queue(next_song_info, current_song_info, handler_input)

class PlaybackStoppedEventHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackStopped Directive received.

    Confirming that the requested audio file stopped playing.
    Do not send any specific response.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackStopped")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackStoppedHandler")

        playback_info = handler_input.attributes_manager.persistent_attributes
        playback_info["current_song"]["current_offset_in_milliseconds"] = handler_input.request_envelope.request.offset_in_milliseconds
        handler_input.attributes_manager.save_persistent_attributes()
        
        return handler_input.response_builder.response

class PlaybackFailedEventHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFailed Directive received."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("AudioPlayer.PlaybackFailed")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackFailedHandler")
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = constants.HELP_MSG

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class RequestLogger(AbstractRequestInterceptor):
    """Log the alexa requests."""
    def process(self, handler_input):
        # type: (HandlerInput) -> None
        logger.debug("Alexa Request: {}".format(
            handler_input.request_envelope.request))

class ResponseLogger(AbstractResponseInterceptor):
    """Log the alexa responses."""
    def process(self, handler_input, response):
        # type: (HandlerInput, Response) -> None
        logger.debug("Alexa Response: {}".format(response))

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


# sb = SkillBuilder()
sb = CustomSkillBuilder(persistence_adapter=s3_adapter, api_client=DefaultApiClient())

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(PlayAudioHandler())
sb.add_request_handler(PauseIntentHandler())
sb.add_request_handler(ResumeIntentHandler())
sb.add_request_handler(PlayNextIntentHandler())
sb.add_request_handler(PlayPreviousIntentHandler())

sb.add_request_handler(PlaybackStartedEventHandler())
sb.add_request_handler(PlaybackFinishedEventHandler())
sb.add_request_handler(PlaybackNearlyFinishedEventHandler())
sb.add_request_handler(PlaybackStoppedEventHandler())
sb.add_request_handler(PlaybackFailedEventHandler())

sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())


# Interceptors
sb.add_global_request_interceptor(RequestLogger())
sb.add_global_response_interceptor(ResponseLogger())

lambda_handler = sb.lambda_handler()