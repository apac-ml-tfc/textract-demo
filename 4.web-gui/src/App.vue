<template>
  <div id="app">
    <div v-if="!signedIn">
      <amplify-authenticator></amplify-authenticator>
    </div>
    <div v-if="signedIn">
      <amplify-sign-out class="signout"></amplify-sign-out>
      <div>Hello <b>{{user.username}}</b></div>
      <img alt="Vue logo" src="./assets/logo.png">
      <h3>Smart OCR demo</h3>
      <SmartOCR/>
    </div>
  </div>
</template>

<script>
import { Logger } from 'aws-amplify';
import SmartOCR from './components/SmartOCR.vue'
import { Auth } from 'aws-amplify'
import { AmplifyEventBus } from 'aws-amplify-vue'

const logger = new Logger('App', 'INFO') // INFO, DEBUG, VERBOSE

export default {
  name: 'App',
  components: {
    SmartOCR
  },
  async beforeCreate() {
    try {
      // for manual browser refreshes while signed in
      const user = await Auth.currentAuthenticatedUser()
      this.signedIn = true
      this.user = user
      logger.debug('beforeCreate/awaits', this.user.username, this.signedIn)
      
    } catch (err) {
      this.signedIn = false
    }
    AmplifyEventBus.$on('authState', info => {
      logger.debug('authState changed', this.user.username, this.signedIn)
      if (info === 'signedIn') {
        this.signedIn = true
          // delay in fetching Auth.user, so wrap setting properties inside
          Auth.currentAuthenticatedUser().then((data) => {
            this.user = data
            this.signedIn = true
            logger.debug('authState changed/currentAuthenticatedUser()', this.user.username)
          });
      } else {
        this.user = {}
        this.signedIn = false
        logger.debug('authState changed/signing out', this.user.username, this.signedIn)
      }
    });
  },
  data() {
    return {
      signedIn: false,
      user: {}
    }
  },
  mounted () {
    logger.info('mounted')
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 10px;
}
.signout {
  background-color: #ededed;
  margin: 0;
  padding: 0px 0px 0px 0px;
}
</style>
