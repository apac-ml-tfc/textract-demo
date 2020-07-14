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
    <b-button v-if="file" variant="success" :disabled="pressed" @click="uploadImage()" style="margin-top: 10px;"
      >{{ pressed ? 'Uploading' : 'Upload' }}</b-button>
    <b-alert :show="Boolean(errorMsg)" variant="danger">{{errorMsg}}</b-alert>
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
              <b-col class="text-left" style="overflow-wrap: break-word;">{{uploadresult.s3objectkey}}</b-col>
            </b-row>
            <b-row>
              <b-col class="text-right">Vendor:</b-col>
              <b-col class="text-left font-weight-bold">{{ocrresult.Vendor && ocrresult.Vendor.Value}}</b-col>
            </b-row>
            <b-row>
              <b-col class="text-right">Date:</b-col>
              <b-col class="text-left font-weight-bold">{{ocrresult.Date && ocrresult.Date.Value}}</b-col>
            </b-row>
            <b-row>
              <b-col class="text-right">Total:</b-col>
              <b-col class="text-left font-weight-bold">{{ocrresult.Total && ocrresult.Total.Value}}</b-col>
            </b-row>
            <b-row v-if="ocrresult.Reviewer">
              <b-col class="text-right">Reviewer:</b-col>
              <b-col class="text-left font-weight-bold">{{ocrresult.Reviewer}}</b-col>
            </b-row>
          </b-container>
          <hr v-if="resultMsg"/>
          <b-alert :show="Boolean(resultMsg)">{{resultMsg}}</b-alert>

        </b-col>
      </b-row>
    </b-container>

    <hr v-if="events && events.length"/>
    <b-container v-if="events && events.length">
      <b-row>
        <b-col>
          <h3 style="margin-bottom: 10px;">Processing History</h3>
          <b-table striped :items="events" :fields="event_fields"></b-table>
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

/**
 * Render a (numeric) timestamp to a (nicely sortable, compact) ISO string in local timezone
 */
function tsToLocalISOString(ts) {
  const tzoffset = new Date().getTimezoneOffset() * 60000;
  return new Date(ts - tzoffset).toISOString();
}

export default {
  name: 'SmartOCR',
  props: {
    msg: String
  },
  data () {
    return {
      errorMsg: null,
      event_fields: [
        { key: "timestamp", sortable: true },
        { key: "eventType" },
        { key: "state" },
      ],
      events: [],
      resultMsg: null,
      photoPickerConfig,
      file: null,
      pressed: false,
      s3objecturl: null,
      uploadresult: {},
      lastUpdateTs: -Infinity,
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
    // Since it's just one topic per user, we can start the subscription process before even uploading:
    this.subscribeNotifications();
  },
  methods: {
    uploadImage: async function () {
      if (this.file) {
        this.ocrstatus = 'Uploading...'
        this.errorMsg = null;
        this.events = [];
        this.resultMsg = null;
        this.pressed = true
        this.uploadresult = {}
        this.uploadprogress_loaded = 0;
        this.uploadprogress_total = 100;
        this.ocrresult = {}
        const me = this;
        logger.info('uploading image', this.file.name, this.file.type)
        await Storage.put(IMAGEUPLOADPATH + this.file.name, this.file, {
            level: 'private',
            contentType: this.file.type,
            progressCallback(progress) {
              me.uploadprogress_loaded = progress.loaded;
              me.uploadprogress_total = progress.total;
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
      this.ocrstatus = 'Starting...';
      
      // Init subscription again in case it failed on mount and re-trying succeeds:
      this.subscribeNotifications();
    },
    fetchImage: async function (key) {
      this.s3objecturl = await Storage.get(key, { level: 'private' })
      logger.debug('s3objecturl:',this.s3objecturl)
    },
    /**
     * Process notifications from the IoT topic to update component view
     * 
     * What we receive is basically AWS Step Functions event objects, with a little pre-processing. There's
     * loads more we could do with this function, or more of the heavy lifting could be shifted to the 
     * notify-sfn-progress Lambda which generates IoT messages from SFn events, to keep the messages small
     * and the client simple.
     */
    processNotification: function (data) {
      logger.info('Message received', data);
      // Check for recency in case messages arrive out-of-order:
      if ((data.value.timestamp >= this.lastUpdateTs) || !data.value.timestamp) {
        if (data.value.type == 'ExecutionSucceeded') {
          this.ocrstatus = 'SUCCEEDED';
          try {
            const output = JSON.parse(data.value.details.output);
            if (output.HumanReview) {
              ['Date', 'Total', 'Vendor'].forEach((k) => {
                this.ocrresult[k] = {
                  Confidence: output.HumanReview[k] ? 1 : 0,
                  Value: output.HumanReview[k],
                };
              });
              if (output.HumanReview.WorkerId) this.ocrresult.Reviewer = output.HumanReview.WorkerId;
              this.ocrresult.Confidence = 1;
              this.resultMsg = 'Processed successfully with human review';
            } else if (output.ModelResult) {
              this.ocrresult = output.ModelResult;
              this.resultMsg = 'Processed successfully with model only (no review required)';
            } else {
              throw new Error(
                "Neither HumanReview nor ModelResult key found on 'successful' state machine output"
              );
            }
          } catch (err) {
            logger.error(err);
            this.resultMsg = "Execution succeeded, but wasn't able to extract result from the notification!";
          }
        } else if (data.value.type.startsWith('Execution') && data.value.type != 'ExecutionStarted') {
          this.ocrstatus = `FAILED - ${data.value.type}`;
          // Build up a result message from error & cause information if present:
          this.resultMsg = data.value.details.error || '';
          if (data.value.details.cause) {
            // 'cause' might be a simple string (generated by Sfn itself) or a JSON string (generated by a
            // called Lambda function)
            let causeMsg;
            try {
              const parsedCause = JSON.parse(data.value.details.cause);
              if (parsedCause && typeof parsedCause === 'object') {
                const causeMsgKey = Object.keys(parsedCause).find(
                  (k) => k.toLowerCase().indexOf('message') >= 0
                );
                causeMsg = causeMsgKey ? parsedCause[causeMsgKey] : parsedCause;
              } else {
                causeMsg = parsedCause;  // At least it parsed, so keep that
              }
            } catch (err) {
              causeMsg = data.value.details.cause;
            }
            if (this.resultMsg) {
              this.resultMsg = `${this.resultMsg}: ${causeMsg}`;
            } else {
              this.resultMsg = data.value.details.cause;
            }
          }
        } else if (data.value.stateName) {
          this.ocrstatus = `RUNNING - ${data.value.stateName}`;
        } else if (this.ocrstatus == 'Starting...') {
          this.ocrstatus = 'RUNNING';
        }

        // TODO: Improve out-of-order event processing to establish a more robust history.
        this.events.unshift({
          timestamp: tsToLocalISOString(data.value.timestamp),
          eventType: data.value.type,
          state: data.value.stateName,
        })
      } else {
        logger.info('Discarded outdated message');
      }
    },
    subscribeNotifications: async function () {
      if (!this.subscribed) {
        logger.debug('Subscribing to notifications...');
        try {
          const creds = await Auth.currentCredentials();
          logger.debug('cognitoIdentityId: ', creds.identityId);

          logger.debug('Adding AWSIoTProvider');
          Amplify.addPluggable(new AWSIoTProvider({
            aws_pubsub_region: AWS_PUBSUB_REGION,
            aws_pubsub_endpoint: AWS_PUBSUB_ENDPOINT,
            clientId: creds.identityId,
          }));

          const topic = this.OCRTopicPrefix + '/' + creds.identityId;
          logger.debug('topic:', topic);

          /*
          Current design is to subcribe to a topic for the authenticated user hence only subscribe once per
          session. Alternate design is to use the s3objectkey as topic, and unsub/sub again per uploads.

          TODO: unsub topic upon logout
          */
         const me = this;
         logger.info(me);
          PubSub.subscribe(topic, { provider: 'AWSIoTProvider' }).subscribe({
            next: data => {
              me.subscribed = true;  // In case we get an error but then continue receiving messages
              me.processNotification(data);
            },
            error: error => {
              logger.error(error);
              me.errorMsg = 'Error from notifications service - updates may not display';
              me.subscribed = false;  // Sometimes this is all the error we get to indicate it's broken
            },
            close: () => {
              logger.warn('Disconnected');
              me.subscribed = false;
            },
          });
          this.subscribed = true;
        } catch (err) {
          logger.error(err);
          logger.warn("Can't connect to notifications service - updates will not display");
          this.errorMsg = "Can't connect to notifications service - updates will not display";
        }
      } else {
        logger.debug('Already subscribed to notifications');
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
