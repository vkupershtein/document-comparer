<template>
    <div class="mb-6">
      <div class="flex justify-between items-center mb-2">
        <span class="font-semibold">Page {{ pageNumber }} of {{ numPages }}</span>
        <div class="flex gap-2">
          <Button icon="pi pi-chevron-left" label="Previous" @click="prevPage" :disabled="pageNumber <= 1" />
          <Button icon="pi pi-chevron-right" label="Next" @click="nextPage" :disabled="pageNumber >= numPages" />
        </div>
      </div>
  
      <div class="relative border shadow-md rounded overflow-scroll max-h-[25rem]">
        <canvas ref="canvas" :style="{ display: 'block', width: '100%' }" />
      </div>
  
      <div class="flex gap-4 mt-4">
        <div>
          <label class="block font-medium mb-1">Header (px)</label>
          <InputNumber v-model="headerCrop" :min="0" :max="maxHeight" />
          <Slider v-model="headerCrop" :max="maxHeight" class="mt-3" />
        </div>
        <div>
          <label class="block font-medium mb-1">Footer (px)</label>
          <InputNumber v-model="footerCrop" :min="0" :max="maxHeight" />
          <Slider v-model="footerCrop" :max="maxHeight" class="mt-3" />
        </div>
      </div>
    </div>
  </template>
  
<script setup>
  import { ref, watch, onMounted } from 'vue';
  import * as pdfjsLib from 'pdfjs-dist';
  import workerSrc from 'pdfjs-dist/build/pdf.worker?worker&url'
  import InputNumber from 'primevue/inputnumber';
  import Button from 'primevue/button';
  import Slider from 'primevue/slider'; 

  pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;
  
  const props = defineProps({
    file: File
  });
  
  const headerCrop = defineModel('headerCrop');
  const footerCrop = defineModel('footerCrop');
  const canvas = ref(null);
  const maxHeight = ref(250);
  const pageNumber = ref(1);
  const numPages = ref(1);
  let pdfDoc = null;
  const previewScale = 0.5;

    const loadPdf = async () => {
        const reader = new FileReader();
        reader.onload = async () => {
            const typedArray = new Uint8Array(reader.result);
            pdfDoc = await pdfjsLib.getDocument({ data: typedArray }).promise;
            numPages.value = pdfDoc.numPages;
            renderPage();
        };
        reader.readAsArrayBuffer(props.file);
    };

    const renderPage = async () => {
        const page = await pdfDoc.getPage(pageNumber.value);
        const viewport = page.getViewport({ scale: previewScale });
        const context = canvas.value.getContext('2d');
        canvas.value.height = viewport.height;
        canvas.value.width = viewport.width;        

        const renderContext = {
            canvasContext: context,
            viewport
        };
        await page.render(renderContext).promise;
        drawOverlay();
    };

    const prevPage = () => {
        if (pageNumber.value > 1) {
            pageNumber.value--;
            renderPage();
        }
    };

    const nextPage = () => {
        if (pageNumber.value < numPages.value) {
            pageNumber.value++;
            renderPage();
        }
    };   
  
    const drawOverlay = () => {
        const ctx = canvas.value.getContext('2d');

        // Top crop
        if (headerCrop.value > 0) {
            ctx.fillStyle = 'rgba(255, 0, 0, 0.3)';
            ctx.fillRect(0, 0, canvas.value.width, headerCrop.value * previewScale);
        }

        // Bottom crop
        if (footerCrop.value > 0) {
            ctx.fillStyle = 'rgba(255, 0, 0, 0.3)';
            ctx.fillRect(0, canvas.value.height - footerCrop.value * previewScale, 
            canvas.value.width, canvas.value.height);
        }
    };
  
  watch(() => props.file, loadPdf);

  watch([headerCrop, footerCrop], () => renderPage());
  
  onMounted(() => {
    if (props.file) {
      loadPdf();
    }
  }); 
      
</script>
  
<style scoped>
  .pdf-preview-container {
    max-width: 100%;
    overflow: auto;
  }
  canvas {
    display: block;
    margin: auto;
    max-width: 100%;
  }
</style>
  