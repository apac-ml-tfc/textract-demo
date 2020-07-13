<template>
  <div class="container">
    <b-form-file
      accept="image/*"
      v-model="file"
      :state="Boolean(file)"
      placeholder="Choose a file or drop it here..."
      drop-placeholder="Drop file here..."
    ></b-form-file>
    <!--<div class="mt-3">Selected file: {{ file ? file.name : '' }}</div>-->
    <div v-if="pressed">
      <b-progress :value="uploadprogress_loaded" :max="uploadprogress_total" show-value animated></b-progress>
    </div>
    <div v-if="file">
      <b-button variant="success" :disabled="pressed" @click="uploadImage()">{{ pressed ? 'Uploading' : 'Upload' }}</b-button>
    </div>
    
    <hr/>

    <b-container v-if="uploadresult.s3objectkey" class="bv-example-row">
      <b-row>
        <b-col>
          <b-img thumbnail fluid :src="s3objecturl" :alt="uploadresult.s3objectkey"></b-img>
        </b-col>
        <b-col>

          <b-container fluid>
            <b-row>
              <b-col class="text-right">Status:</b-col>
              <b-col class="text-left">{{ocrstatus}}</b-col>
            </b-row>
            <b-row>
              <b-col class="text-right">File:</b-col>
              <b-col class="text-left">{{uploadresult.s3objectkey}}</b-col>
            </b-row>
            <b-row>
              <b-col class="text-right">Vendor:</b-col>
              <b-col class="text-left font-weight-bold">{{ocrresult.vendor}}</b-col>
            </b-row>
            <b-row>
              <b-col class="text-right">Date:</b-col>
              <b-col class="text-left font-weight-bold">{{ocrresult.date}}</b-col>
            </b-row>
            <b-row>
              <b-col class="text-right">Total:</b-col>
              <b-col class="text-left font-weight-bold">{{ocrresult.total}}</b-col>
            </b-row>
          </b-container>

        </b-col>
      </b-row>
    </b-container>

  </div>
</template>

<script>
import { Logger } from 'aws-amplify';
import { Auth } from 'aws-amplify'
import Amplify, { PubSub } from 'aws-amplify'
import { AWSIoTProvider } from '@aws-amplify/pubsub/lib/Providers'
import { Storage } from 'aws-amplify'

//Amplify.Logger.LOG_LEVEL = 'VERBOSE'
const logger = new Logger('SmartOCR', 'DEBUG'); // INFO, DEBUG, VERBOSE

const IMAGEUPLOADPATH = ''
const photoPickerConfig = {
  path: IMAGEUPLOADPATH,
  storageOptions: {
    level: 'private'
  }
}
const AWS_PUBSUB_REGION = process.env.VUE_APP_PUBSUB_REGION;
const AWS_PUBSUB_ENDPOINT = `wss://${process.env.VUE_APP_PUBSUB_ENDPOINT}/mqtt`;

logger.debug(`Connecting to ${AWS_PUBSUB_ENDPOINT} (${AWS_PUBSUB_REGION})`);

export default {
  name: 'SmartOCR',
  props: {
    msg: String
  },
  data () {
    return {
      photoPickerConfig,
      file: null,
      pressed: false,
      s3objecturl: null,
      uploadresult: {},
      identityId: null,
      OCRTopicPrefix: 'private',
      uploadprogress_loaded: 0,
      uploadprogress_total: 100,
      subscribed: false,
      ocrresult: {},
      ocrstatus: ''
    }
  },
  mounted () {
    logger.info('mounted')
  },
  methods: {
    uploadImage: async function () {
      if (this.file) {
        this.ocrstatus = 'Uploading...'
        this.pressed = true
        this.uploadresult = {}
        this.ocrresult = {}
        const foo = this
        logger.info('uploading image', this.file.name, this.file.type)
        await Storage.put(IMAGEUPLOADPATH + this.file.name, this.file, {
            level: 'private',
            contentType: this.file.type,
            progressCallback(progress) {
              foo.uploadprogress_loaded = progress.loaded
              foo.uploadprogress_total = progress.total
            },
        })
        .then (putresult => this.uploadSuccess(putresult))
        .catch(err => logger.error(err));
        this.file = null
        this.pressed = false
      }
    },
    uploadSuccess: async function (putresult) {
      this.uploadresult.s3objectkey = putresult.key
      logger.info('upload success. S3objectkey:', this.uploadresult)
      
      this.fetchImage(this.uploadresult.s3objectkey)
      this.ocrstatus = 'OCR...'
      
      // listen for pubsub topic for OCR results
      this.subscribeOCRTopic()
      
    },
    fetchImage: async function (key) {
      this.s3objecturl = await Storage.get(key, { level: 'private' })
      logger.debug('s3objecturl:',this.s3objecturl)
    },
    subscribeOCRTopic: async function () {
      logger.debug('subscribed:', this.subscribed)
      if (!this.subscribed) {
        
        await Auth.currentCredentials()
        logger.debug('Adding AWSIoTProvider')
        Amplify.addPluggable(new AWSIoTProvider({
          aws_pubsub_region: AWS_PUBSUB_REGION,
          aws_pubsub_endpoint: AWS_PUBSUB_ENDPOINT
        }))
        
        const authCheck = this
        await Auth.currentCredentials().then((info) => {
          authCheck.identityId = info.identityId;
        });
        logger.debug('cognitoIdentityId: ', this.identityId)
        const topic = this.OCRTopicPrefix + '/' + this.identityId
        logger.debug('topic:', topic)
 
        /*
        topic: private/us-east-1:073c31fb-efea-434d-ac4c-caccbce7d42a
        
        Current design is to subcribe to a topic for the authenticated user hence only subscribe once per session.
        Alternate design is to use the s3objectkey as topic, and unsub/sub again per uploads.
        
        TODO: unsub topic upon logout
        
        message:
        {
           "bucket":"smartocr-uploads31839-dev",
           "id":"private/us-east-1:073c31fb-efea-434d-ac4c-caccbce7d42a",
           "key":"private/us-east-1:073c31fb-efea-434d-ac4c-caccbce7d42a/X51008099047_canocr.jpg",
           "status":"Completed",   // "Completed", "Pending human review"
           "result":{
              "vendor":"XYZ co",
              "date":"1/1/2020",
              "total":"123.45"
           }
        }
        */
        PubSub.subscribe(topic, { provider: 'AWSIoTProvider' }).subscribe({
          next: data => {
            logger.info('Message received', data)
            this.ocrstatus = data.value.status
            if (this.ocrstatus.toLowerCase()=="completed") {
              this.ocrresult = data.value.result
              logger.debug('this.ocrresult', this.ocrresult)
            } else {
              this.ocrresult = ''
            }
          },
          error: error => logger.error(error),
          close: () => logger.info('Done'),
        });
        this.subscribed = true
      }
    },
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
h3 {
  margin: 40px 0 0;
}
ul {
  list-style-type: none;
  padding: 0;
}
li {
  display: inline-block;
  margin: 0 10px;
}
a {
  color: #42b983;
}
</style>
