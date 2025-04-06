<template>
    <div class="formatted-text">
        <span
        v-for="(chunk, index) in text"
        :key="index"
        :class="tagClass(chunk.tag)"
        >
        {{ chunk.subtext }}
        </span>
    </div>
</template>
  
<script setup>
  import { defineProps } from 'vue';
  
  const props = defineProps({
    text: {
      type: [String, Array],
      required: false,
      default: ""
    }
  });
  
  const tagClass = (tag) => {
    switch (tag) {
      case 'equal':
        return 'text-equal';
      case 'insert':
        return 'text-insert';
      case 'delete':
        return 'text-delete';
      case 'replace':
        return 'text-replace';
      default:
        return '';
    }
  };
</script>
  
<style scoped>
  .text-equal {
    background-color: transparent;
  }
  .text-insert {
    background-color: #d4edda;
  }
  .text-delete {
    background-color: #f8d7da;
  }
  .text-replace {
    background-color: #fff3cd;
  }
</style>