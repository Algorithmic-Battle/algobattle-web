<script setup lang="ts">
import { login as loginRequest } from "@client";
import { ref } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const email = ref("");
const msg = ref("");

async function submitLogin() {
  try {
    await loginRequest({ target_url: route.fullPath, body: email.value });
    msg.value = "email_sent";
  } catch {
    msg.value = "error";
  }
}
</script>

<template>
  <div class="dropdown-menu dropdown-menu-end" id="outer">
    <div v-if="msg == 'error'" class="alert alert-danger" role="alert">
      There was an error logging you in.
    </div>
    <div v-if="msg == 'email_sent'" class="alert alert-success" role="alert">
      A login email has been sent to the address if it is registered to a user.
    </div>
    <div class="mb-3">
      <label for="email" class="form-label">Email address</label>
      <input type="email" class="form-control" id="email" autocomplete="email" required v-model="email" @keyup.enter="submitLogin" />
    </div>
    <button type="button" class="btn btn-primary" @click="submitLogin">Send login link</button>
  </div>
</template>

<style scoped>
.dropdown-menu {
  min-width: 340px;
  padding: 20px;
}
</style>
