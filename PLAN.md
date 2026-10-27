# PLAN

## Goal
Create application which will sequentially(as ordered): 
1. listen on live session(which is conversation between several people) to several audio input devices(e.g microphone,system audio output etc...) which will be specified by application runner
2. do automatic speech recognition on captured audio,produce armenian transcriptions
3. translate produced armenian translations into english text
4. diarize who spoke(in case of audio coming from microphone it should always show Me,otherwise Speaker N)
5. show armenian text with corresponding english translations,speaker number and datetime in terminal when the conversation is still running on terminal in live

**In addition to project goal**
- By this project goal description,second and third step being separate or being merged is under question and should be determined when discussed about project architecture.
- Apllication will not remember speakers between different sessions,only for the specific one session in which they speak and for the whole duration of that session.


## First walking skeleton
**First we will create a walking skeleton of application which means it will take audio,give transcriptions,translate them and show them in terminal.In my opinion after completing this skeleton,we will add diarization,and then improve application by first identifying it's weakest points and improving them.During improvement of application we will only improve the required parts of application not adding anything out of our scope.Also in our first steps we should collect small amount of audio conversations with corresponding transcriptions,translations and datetime of speech.This being said we first should choose models in a way to be sure it will work on local machine almost surely,not being much advanced on first choices.**

## Out of scope 

- We will use only terminal to show texts (no graphical interface is needed)
- no installers or packaged apps
- no saving transcripts to file
- no echo handling

## Constraints 
- End to end latency of application meaning from the end of spoken phrase on Armenian to its English line in the terminal should be at most 5 seconds.
- Translation,transcription speaker identification will run on my own laptop.No cloud speech or translation APIs.
- Code development will be done on Python programming language,and we can use any libraries and models,as long as they run locally.


**Important**
- By locally and my own laptop I mean that everything should work on the local computer on which you will do development,so ask all the clarifying questions about local laptop needed for application to work on local laptop.

## Predecided modules 
**These are the modules which are predecided with initial research on the project goal and may be changed,by clarifying questions if you will have better ideas(based on the fact that you have better ideas on project architecture,or module division).**
- audio_capture
INPUT: chosen(by user) input devices from which application will capture audio at the same time
OUTPUT: input audio(needed for asr) and the same input audio VAD segmented(for diarizer)
- diarizer
INPUT: VAD segmented audio
OUTPUT: a speaker label for each input segment (Me for microphone segments; Speaker N for system-audio segments, stable for the whole session).
- asr
INPUT: input audio(which will be only on Armenian)
OUTPUT: Armenian transcriptions
- translate 
INPUT: Armenian transcriptions
OUTPUT: English translations
- output
INPUT: Armenian translations
OUTPUT: live Armenian text(from spoken speech in live) corresponding datetime,speaker number(time counting from start of conversation)


**Important**
- This module division is done based on initial research and is subject to change if better(better means that we have both discussed on that and came to point when we think it is better) solutions exist.As for initial research,I found that diarization can be done with audio segmentation with VAD then for example clusterization algorithm.Pros required for project in this approach is that it is lightweight,which is in my opinion needed for 'first walking skeleton' approach.Also the translation and asr modules is not yet decided will they be merged(using one step model with asr and model translation) or application will work with separate asr and machine translation models
- For the audio_capture to capture from all the input devices simultaneously at the same time as an important fact the local laptop(with Ubuntu) uses Pulseaudio

## Deliverables

A git repository containing:
1. The source code
2. A README covering:
- How to set up and run,including the audio device setup
- which models did we choose,the alternatives that we considered and why we decided as we did
- a short architecture about how pieces fit together
- known limitations of application and what we would improve if we had more time because we have time limitation,on which I will give signal when we will approach to the end of our development
3. chats folder with all our chat transcriptions exported into it as .md files


## How we will test

- For working skeleton test first we will collect few Armenian audio conversations with their,transcriptions and if possible also with their corresponding dates when the speech was spoken
- We will use the collected small data as initial evaluation data.Further collection of big amount of data will be done after the working skeleton of application will be ready
- We will collect test and QA questions in TEST.md(for example results of tests) and in other test files during the work,which we will also run in the end of buliding application.Every part(what will be written into it,what status each test has,passed or not passed) of TEST.md should be agreed with me then written into it.
- When codebase will grow we will isolate each big codeblock,test it on it's own and then only merge to project.

## Risks to consider
- Risk: Latency exceeds 5s limit.Mitigation: Use Build early tests for the whole flow,so that we could monitor the 5s limit is not exceeded.
- Risk: During work redeciding the same thing many times which will waste time. Mitigation: Writing stable rules,important observations and decisions in DECISIONS.md so that we will remember important things in DECISIONS.md.This also relates to the fact that PLAN.md should be also extracted into DECISIONS.md.
- Risk: Writing wrong and big commits in project. Mitigation All the git commands should be discussed and git commits should be small,but you have permission to propose commit if the step is small and accomplishes some step of bigger work.You have no permission to write git commmands without my permission,but you have permission to propose git commit if we have done some small step 
- Risk: The created app not working on local laptop.Mitigation: Exploring local laptop's needed requirements early and having answers on required questions that are essential for the furthed exploration of which frameworks to use on local laptop.

**Important**
- We will write all the decisions,stable rules(for example style,structure,'never do X'),project status,on which step we are into DECISIONS.md file adding everything with small human readable steps so that everything can be controlled by me