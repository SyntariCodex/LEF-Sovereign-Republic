import ssl
import nltk

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

print("Downloading NLTK data...")
nltk.download('brown')
nltk.download('punkt')
# nltk.download('punkt_tab') # Try this if punkt fails
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
print("Done.")
