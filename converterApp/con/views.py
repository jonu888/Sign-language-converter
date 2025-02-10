# views.py

from django.shortcuts import render
from .forms import VideoUploadForm
import speech_recognition as sr
import tempfile
import os


try:
    from moviepy import VideoFileClip
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "moviepy"])
    from moviepy import VideoFileClip

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
from django.contrib.staticfiles import finders


def ensure_nltk_data():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        nltk.download('wordnet')
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')
    try:
        nltk.data.find('taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download('averaged_perceptron_tagger')


def home_view(request):
    return render(request, 'home.html')

def about_view(request):
    return render(request, 'about.html')

def contact_view(request):
    return render(request, 'contact.html')

# @login_required(login_url="login")
def upload_video(request):
    ensure_nltk_data()
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Process the uploaded video
            uploaded_video = request.FILES['video']

            # Save the uploaded video to a temporary file
            with open('uploaded_video.mp4', 'wb+') as destination:
                for chunk in uploaded_video.chunks():
                    destination.write(chunk)

            # Get the path to the saved temporary file
            video_path = os.path.abspath('uploaded_video.mp4')

            # Extract audio from the video
            video = VideoFileClip(video_path)
            audio = video.audio

            # Save audio as temporary WAV file
            temp_audio_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_audio_path = temp_audio_file.name
            audio.write_audiofile(temp_audio_path)
            temp_audio_file.close()

            # Convert audio to text
            recognizer = sr.Recognizer()
            with sr.AudioFile(temp_audio_path) as source:
                audio_data = recognizer.record(source)
                try:
                    text = recognizer.recognize_google(audio_data)
                except sr.UnknownValueError:
                    text = "Speech recognition could not understand the audio"
                except sr.RequestError as e:
                    text = f"Could not request results from Google Speech Recognition service; {e}"
                except Exception as e:
                    text = f"An error occurred during speech recognition: {e}"
    
            # Clean up temporary file
            os.unlink(temp_audio_path)
            print("Text from video:", text)
            text = text.lower()
            words = word_tokenize(text)

            tagged = nltk.pos_tag(words)
            tense = {
                "future": len([word for word in tagged if word[1] == "MD"]),
                "present": len([word for word in tagged if word[1] in ["VBP", "VBZ", "VBG"]]),
                "past": len([word for word in tagged if word[1] in ["VBD", "VBN"]]),
                "present_continuous": len([word for word in tagged if word[1] in ["VBG"]]),
            }
  
            # stopwords that will be removed
            stop_words = set([
                "mightn't", 're', 'wasn', 'wouldn', 'be', 'has', 'that', 'does', 'shouldn', 'do', "you've", 'off', 'for',
                "didn't", 'm', 'ain', 'haven', "weren't", 'are', "she's", "wasn't", 'its', "haven't", "wouldn't", 'don',
                'weren', 's', "you'd", "don't", 'doesn', "hadn't", 'is', 'was', "that'll", "should've", 'a', 'then', 'the',
                'mustn', 'i', 'nor', 'as', "it's", "needn't", 'd', 'am', 'have', 'hasn', 'o', "aren't", "you'll",
                "couldn't", "you're", "mustn't", 'didn', "doesn't", 'll', 'an', 'hadn', 'whom', 'y', "hasn't", 'itself',
                'couldn', 'needn', "shan't", 'isn', 'been', 'such', 'shan', "shouldn't", 'aren', 'being', 'were', 'did',
                'ma', 't', 'having', 'mightn', 've', "isn't", "won't"
            ])

        # removing stopwords and applying lemmatizing nlp process to words
            lr = WordNetLemmatizer()
            filtered_text = []
            for w, p in zip(words, tagged):
                if w not in stop_words:
                    if p[1] == 'VBG' or p[1] == 'VBD' or p[1] == 'VBZ' or p[1] == 'VBN' or p[1] == 'NN':
                        filtered_text.append(lr.lemmatize(w, pos='v'))
                    elif p[1] == 'JJ' or p[1] == 'JJR' or p[1] == 'JJS' or p[1] == 'RBR' or p[1] == 'RBS':
                        filtered_text.append(lr.lemmatize(w, pos='a'))
                    else:
                        filtered_text.append(lr.lemmatize(w))

            # adding the specific word to specify tense
            words = filtered_text
            temp = []
            for w in words:
                if w == 'I':
                   temp.append('Me')
                else:
                   temp.append(w)
            words = temp
            probable_tense = max(tense, key=tense.get)

            if probable_tense == "past" and tense["past"] >= 1:
               temp = ["Before"]
               temp = temp + words
               words = temp
            elif probable_tense == "future" and tense["future"] >= 1:
                if "Will" not in words:
                   temp = ["Will"]
                   temp = temp + words
                   words = temp
                else:
                   pass
            elif probable_tense == "present":
                if tense["present_continuous"] >= 1:
                    temp = ["Now"]
                    temp = temp + words
                    words = temp

            filtered_text = []
            for w in words:
                path = w + ".mp4"
                f = finders.find(path)
                # splitting the word if its animation is not present in database
                if not f:
                    for c in w:
                        filtered_text.append(c)
                # otherwise animation of word
                else:
                    filtered_text.append(w)
            words = filtered_text

            return render(request, 'animation.html', {'text': text,'words':words})
    else:
        form = VideoUploadForm()
    return render(request, 'animation.html', {'form': form})

#@login_required(login_url="login")
def animation_view(request):
    ensure_nltk_data()
    if request.method == 'POST':
        text = request.POST.get('sen')
        # tokenizing the sentence
        text = text.lower()
        words = word_tokenize(text)

        tagged = nltk.pos_tag(words)
        tense = {
            "future": len([word for word in tagged if word[1] == "MD"]),
            "present": len([word for word in tagged if word[1] in ["VBP", "VBZ", "VBG"]]),
            "past": len([word for word in tagged if word[1] in ["VBD", "VBN"]]),
            "present_continuous": len([word for word in tagged if word[1] in ["VBG"]]),
        }

        # stopwords that will be removed
        stop_words = set([
            "mightn't", 're', 'wasn', 'wouldn', 'be', 'has', 'that', 'does', 'shouldn', 'do', "you've", 'off', 'for',
            "didn't", 'm', 'ain', 'haven', "weren't", 'are', "she's", "wasn't", 'its', "haven't", "wouldn't", 'don',
            'weren', 's', "you'd", "don't", 'doesn', "hadn't", 'is', 'was', "that'll", "should've", 'a', 'then', 'the',
            'mustn', 'i', 'nor', 'as', "it's", "needn't", 'd', 'am', 'have', 'hasn', 'o', "aren't", "you'll",
            "couldn't", "you're", "mustn't", 'didn', "doesn't", 'll', 'an', 'hadn', 'whom', 'y', "hasn't", 'itself',
            'couldn', 'needn', "shan't", 'isn', 'been', 'such', 'shan', "shouldn't", 'aren', 'being', 'were', 'did',
            'ma', 't', 'having', 'mightn', 've', "isn't", "won't"
        ])

        # removing stopwords and applying lemmatizing nlp process to words
        lr = WordNetLemmatizer()
        filtered_text = []
        for w, p in zip(words, tagged):
            if w not in stop_words:
                if p[1] == 'VBG' or p[1] == 'VBD' or p[1] == 'VBZ' or p[1] == 'VBN' or p[1] == 'NN':
                    filtered_text.append(lr.lemmatize(w, pos='v'))
                elif p[1] == 'JJ' or p[1] == 'JJR' or p[1] == 'JJS' or p[1] == 'RBR' or p[1] == 'RBS':
                    filtered_text.append(lr.lemmatize(w, pos='a'))
                else:
                    filtered_text.append(lr.lemmatize(w))

        # adding the specific word to specify tense
        words = filtered_text
        temp = []
        for w in words:
            if w == 'I':
                temp.append('Me')
            else:
                temp.append(w)
        words = temp
        probable_tense = max(tense, key=tense.get)

        if probable_tense == "past" and tense["past"] >= 1:
            temp = ["Before"]
            temp = temp + words
            words = temp
        elif probable_tense == "future" and tense["future"] >= 1:
            if "Will" not in words:
                temp = ["Will"]
                temp = temp + words
                words = temp
        elif probable_tense == "present":
            if tense["present_continuous"] >= 1:
                temp = ["Now"]
                temp = temp + words
                words = temp

        filtered_text = []
        for w in words:
            path = w + ".mp4"
            f = finders.find(path)
            # splitting the word if its animation is not present in database
            if not f:
                for c in w:
                    filtered_text.append(c)
            # otherwise animation of word
            else:
                filtered_text.append(w)
        words = filtered_text

        return render(request, 'animation1.html', {'words': words, 'text': text})
    else:
        return render(request, 'animation1.html')


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # log the user in
            return redirect('animation')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            # log in user
            user = form.get_user()
            login(request, user)
            if 'next' in request.POST:
                return redirect(request.POST.get('next'))
            else:
                return redirect('animation')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect("home")