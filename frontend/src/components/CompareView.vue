<template>
  <div>
    <form class="flex flex-col gap-2 justify-center w-md m-4" @submit.prevent="submitFiles">
      <input class="p-1 cursor-pointer" type="file" @change="handleFileUpload($event, 'left')" accept="application/pdf" required />
      <input class="p-1 cursor-pointer" type="file" @change="handleFileUpload($event, 'right')" accept="application/pdf" required />
      <button type="submit">Compare</button>
    </form>

    <ProgressSpinner v-if="loading" style="width: 50px; height: 50px;" strokeWidth="8" fill="transparent" animationDuration=".5s" aria-label="Loading" />

    <DataTable v-if="comparisonResults.length > 0" :value="comparisonResults" paginator :rows="100" scrollable scrollHeight="600px" tableStyle="min-width: 50rem">
      <template #header>
        <div class="flex justify-start gap-2">
          <button class="mr-3" @click="exportToExcel">Export to Excel</button>
          <button class="mr-3" @click="exportToPDF">Export to PDF</button>
        </div>
      </template>
      <Column field="type" header="Type" frozen />
      <Column field="ratio" header="Similarity Ratio" frozen />
      <Column field="heading_number_left" header="Heading # Left" />
      <Column field="heading_text_left" header="Heading Left" />
      <Column header="Text Left">
        <template #body="slotProps">
          <FormattedText :text="slotProps.data.text_left_report" />
        </template>
      </Column>      
      <Column field="heading_number_right" header="Heading # Right" />
      <Column field="heading_text_right" header="Heading Right" />
      <Column header="Text Right">
        <template #body="slotProps">
          <FormattedText :text="slotProps.data.text_right_report" />
        </template>
      </Column>      
      
    </DataTable>
  </div>
</template>
  
<script setup>
  import { ref } from 'vue';
  import axios from 'axios';
  import ProgressSpinner from 'primevue/progressspinner';
  import DataTable from 'primevue/datatable';
  import Column from 'primevue/column';
  import FormattedText from '../components/FormattedText.vue';
  import * as XLSX from 'xlsx';
  import jsPDF from 'jspdf';
  import autoTable from 'jspdf-autotable';

  const leftFile = ref(null);
  const rightFile = ref(null);
  const loading = ref(false);
  const comparisonResults = ref([]);

  const handleFileUpload = (event, side) => {
    const file = event.target.files[0];
    if (side === 'left') leftFile.value = file;
    else rightFile.value = file;
  };

  
  const submitFiles = async () => {
    if (!leftFile.value || !rightFile.value) {
      alert('Please select both PDF files.');
      return;
    }

    loading.value = true;
      
    const formData = new FormData()
    formData.append('left_file', leftFile.value)
    formData.append('right_file', rightFile.value)
    formData.append('header_left', 40)
    formData.append('footer_left', 40)
    formData.append('size_weight_left', 0.8)
    formData.append('header_right', 40)
    formData.append('footer_right', 40)
    formData.append('size_weight_right', 0.8)
    formData.append('ratio_threshold', 0.5)
    formData.append('length_threshold', 30)

    try {
      const response = await axios.post('http://127.0.0.1:8000/upload/', formData);
      comparisonResults.value = response.data.comparison;
    } catch (error) {
      console.error('Error uploading files:', error);
      alert('An error occurred during file upload.');
    } finally {
      loading.value = false;
    }
  }
  
  const exportToExcel = () => {
    const worksheetData = comparisonResults.value.map(result => ({
      'Type': result.type,
      'Similarity Ratio': result.ratio,
      'Heading # Left': result.heading_number_left,
      'Heading Left': result.heading_text_left,
      'Text Left': typeof result.text_left_report === "string" ? result.text_left_report : result.text_left_report.map(x => x.subtext).join(' '),      
      'Heading # Right': result.heading_number_right,
      'Heading Right': result.heading_text_right,
      'Text Right': typeof result.text_right_report === "string" ? result.text_right_report : result.text_right_report.map(x => x.subtext).join(' ')
    }));
    const worksheet = XLSX.utils.json_to_sheet(worksheetData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Comparison');
    XLSX.writeFile(workbook, 'comparison.xlsx');
  };

  const exportToPDF = () => {
    const doc = new jsPDF();
    const tableData = comparisonResults.value.map(result => [
      result.type,
      result.ratio, 
      result.heading_number_left,
      result.heading_text_left,
      typeof result.text_left_report === "string" ? result.text_left_report : result.text_left_report.map(x => x.subtext).join(' '),
      result.heading_number_right,
      result.heading_text_right,
      typeof result.text_right_report === "string" ? result.text_right_report : result.text_right_report.map(x => x.subtext).join(' ') 
    ]);
    autoTable(doc, {
      head: [[
        'Type', 'Similarity Ratio', 'Heading # Left', 'Heading Left', 
        'Text Left', 'Heading # Right', 'Heading Right', 'Text Right'         
      ]],
      body: tableData,
      styles: { fontSize: 8 },
      headStyles: { fillColor: [41, 128, 185] },
    });
    doc.save('comparison.pdf');
  };
</script> 