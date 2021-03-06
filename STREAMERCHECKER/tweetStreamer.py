import tweepy
import json
import time
import datetime
import sys
import random
import threading

#override tweepy.StreamListener to add logic to on_status
class MyStreamListener(tweepy.StreamListener):

    # init object
    def __init__(self):
        super(MyStreamListener, self).__init__()
        self.resetVariables()

    # reset everything
    def resetVariables(self) :
        # get date
        dateTime = datetime.datetime.now().strftime("%d-%m-%Y")

        #self.jsonName = dateTime + "_" + str(hMapped)
        self.jsonName = dateTime
        self.verbose = False
        self.numTweetsSaved = 0
        self.numTweetsAll = 0

    # called when a tweet is received
    def on_status(self, status):
        # perform classification
        if(threading.active_count()) <= 5:
            t = threading.Thread(target=self.processTweet, args=(status,))
            t.start()

    def processTweet(self, _status) :
        #print(status.text)
        #with open('tweet.json', 'w') as outfile:
        #    json.dump(status._json, outfile)

        # increment pulled tweet number
        self.numTweetsAll = self.numTweetsAll + 1

        # analyze tweet
        res, diffTime = self.analyze_tweet(_status, False)

        # save to file
        if(isinstance(res, dict)) :
            self.numTweetsSaved = self.numTweetsSaved + 1
            print("[TWEETSTREAMER]\tTweet received [{}]\tSaving tweet [{}]\tthreads : {}\tDiffTime = {}".format(self.numTweetsAll, self.numTweetsSaved, threading.active_count(), diffTime))
            with open(folderToSave + self.jsonName + '.json', 'a') as outfile:
                json.dump(res, outfile)
                outfile.write('\n')
        else :
            if self.verbose :
                if res == -1 :
                    print("[TWEETSTREAMER]\tTweet received [{}]\tTweet is a retweet... not saving.".format(self.numTweetsAll))
                if res == -2 :
                    print("[TWEETSTREAMER]\tTweet received [{}]\tTweet is a reply... not saving.".format(self.numTweetsAll))
                if res == -3 :
                    print("[TWEETSTREAMER]\tTweet received [{}]\tTweet is a quote... not saving.".format(self.numTweetsAll))
                if res == -4 :
                    print("[TWEETSTREAMER]\tTweet received [{}]\tTweet has a url... not saving.".format(self.numTweetsAll))
                if res == -5 :
                    print("[TWEETSTREAMER]\tTweet received [{}]\tTweet has a mention... not saving.".format(self.numTweetsAll))
                if res == -6 :
                    print("[TWEETSTREAMER]\tTweet received [{}]\tTweet has a media but not photo... not saving.".format(self.numTweetsAll))


    def analyze_tweet(self, status, verbose) :
        # get time of creation
        createdAt = status.created_at
        createdAtTimestamp = datetime.datetime.timestamp(createdAt) - time.timezone  # correct for timezone
        createdAt = datetime.datetime.fromtimestamp(createdAtTimestamp)

        # get current time
        now = datetime.datetime.now()
        nowTimestamp = datetime.datetime.timestamp(now)

        # get diff
        diffTime = int(nowTimestamp - createdAtTimestamp)

        # init json
        jsonData = {}

        # check if retweet
        try:
            status.retweeted_status
            if(verbose) :
                print("RETWEET")
            return -1, diffTime
        except AttributeError:  # Not a Retweet
            if(verbose) :
                print("NOT A RETWEET")

        # check if reply
        if(status.in_reply_to_status_id is not None) :
            if(verbose) :
                print("REPLY")
            return -2, diffTime
        if(verbose) :
            print ("NOT A REPLY")

        # check if quoted
        if(status.is_quote_status) :
            if(verbose) :
                print("QUOTE")
            return -3, diffTime
        if(verbose) :
            print ("NOT A QUOTE")

        # create json
        #post stuff
        jsonData['created_at']          = str(createdAt)
        jsonData['id']                  = status.id
        jsonData['id_str']              = status.id_str
        jsonData['text']                = status.text
        jsonData['retweet_count']       = status.retweet_count
        jsonData['favorite_count']      = status.favorite_count

        # user stuff
        jsonData['user_id']             = status.user.id
        jsonData['user_id_str']         = status.user.id_str
        jsonData['user_name']           = status.user.name
        jsonData['user_screen_name']    = status.user.screen_name
        jsonData['user_followers']      = status.user.followers_count

        # image stuff
        # check if tweet has media
        jsonData['has_image']   = False
        has_media = False
        try:
            medias = status.extended_entities['media']
            has_media = True

            # loop through media
            num_media = 0
            for el in medias:
                # check if photo
                if(el['type'] == 'photo') :
                    num_media += 1

                    # if has at least one image
                    if(num_media == 1) :
                        if(verbose) :
                            print("HAS IMAGE")
                        jsonData['has_image']   = True
                        jsonData['images']      = []

                    # append image
                    jsonData['images'].append({
                        'link'  : el['media_url'] + "?format=jpg&name=large",
                        'w'     : el['sizes']['large']['w'],
                        'h'     : el['sizes']['large']['h']
                    })

        except AttributeError:  # Not a Retweet
            if(verbose) :
                print("HAS NO IMAGE")

        # check if has url
        if(len(status.entities['urls']) > 0) :
            return -4, diffTime

        # check if has mention
        if(len(status.entities['user_mentions']) > 0) :
            return -5, diffTime

        # check if has media but no photo
        if(has_media and not jsonData['has_image']) :
            return -6, diffTime

        return jsonData, diffTime


# folder to save in
folderData = "../DATA/"
folderToSave = folderData + "tweetsUnchecked/"
keyFile = folderData + "keys.json"
configFile = folderData + "config.json"

# get config
with open(configFile, 'r') as f_config :
    config = json.load(f_config)

# get keys and tokens
with open(keyFile, 'r') as f_keys :
    data = json.load(f_keys)
    api_key = data["api_key"]
    api_secret_key = data["api_secret_key"]
    access_token = data["access_token"]
    access_token_secret = data["access_token_secret"]

# authentification and creation of api object
auth = tweepy.OAuthHandler(api_key, api_secret_key)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# stream variable
myStreamListener = MyStreamListener()
myStream = tweepy.Stream(auth = api.auth, listener=myStreamListener, tweet_mode= 'extended')
stream_connected = False
timeStart = 0
waitTime = 0.1

while True :
    # get time
    timeCurrent = time.time()

    # launch stream
    if not stream_connected :
        print("[TWEETSTREAMER @ {}]\tConnect stream".format(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S")))
        myStreamListener.resetVariables()
        myStream.filter(languages=["fr"], track=["je", "le", "la", "les", "tu", "es", "suis", "a", "as", "es", "oui", "non", "y", "et", "pas"], is_async=True)
        stream_connected = True
        timeStart = timeCurrent
        waitTime = 0.1

    # disconnect stream depending on 3 conditions
    # 1- we reached the time limit
    # 2- we received more than a specified number of tweets
    # 3- we stored more than a specified number of tweets
    if myStreamListener.numTweetsAll >= config["tweetStreamerMaxReceived"] or myStreamListener.numTweetsSaved >= config["tweetStreamerMaxStored"] or abs(timeCurrent - timeStart) >= config["tweetStreamerDurationMax"]:
        myStream.disconnect()
        stream_connected = False
        waitTime = config["tweetStreamerWait"]

        # info
        print("[TWEETSTREAMER @ {}]\tDisconnect stream and wait {} seconds".format(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"), waitTime))

    #
    time.sleep(waitTime)
